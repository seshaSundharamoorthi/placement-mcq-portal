from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from config import Config
from database import db, User, Question, Result, UserAnswer, Bookmark
from functools import wraps
from sqlalchemy import func
import csv
import io
import random

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
bcrypt = Bcrypt(app)

# Session Authentication Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized. Please log in.'}), 401
            return redirect(url_for('auth_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized. Admin access required.'}), 403
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth_page'))
        return f(*args, **kwargs)
    return decorated_function


# ==============================================================================
# HTML VIEW ROUTES
# ==============================================================================

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/auth')
def auth_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('auth.html')

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template('student_dashboard.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/test/setup')
@login_required
def test_setup():
    # Get available categories and counts
    categories_query = db.session.query(
        Question.category, func.count(Question.id)
    ).group_by(Question.category).all()
    categories = [{'name': cat, 'count': count} for cat, count in categories_query]
    
    # Get bookmarks count for the student
    bookmarks_count = Bookmark.query.filter_by(user_id=session['user_id']).count()
    
    return render_template('test_setup.html', categories=categories, bookmarks_count=bookmarks_count)

@app.route('/test/take')
@login_required
def test_taking():
    # Parameters parsed on the frontend via JavaScript
    return render_template('test_taking.html')

@app.route('/test/result/<int:result_id>')
@login_required
def test_result(result_id):
    res = Result.query.get_or_404(result_id)
    # Ensure students can only access their own results
    if session.get('role') != 'admin' and res.user_id != session['user_id']:
        flash('Unauthorized to view this result.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    student = User.query.get(res.user_id)
    return render_template('test_result.html', result=res, student_name=student.name)

@app.route('/test/review/<int:result_id>')
@login_required
def review_mistakes(result_id):
    res = Result.query.get_or_404(result_id)
    if session.get('role') != 'admin' and res.user_id != session['user_id']:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    return render_template('review_mistakes.html', result_id=result_id)


# ==============================================================================
# AUTHENTICATION API ROUTES
# ==============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not name or not email or not password:
        return jsonify({'error': 'All fields are required.'}), 400
        
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email is already registered.'}), 400
        
    # Prevent register of predefined admin email as student
    if email == "seshasundharamoorthi2005@gmail.com":
        return jsonify({'error': 'This email is reserved for Admin.'}), 403
        
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(name=name, email=email, password=hashed_pw, role='student')
    db.session.add(user)
    db.session.commit()
    
    # Auto login after register
    session['user_id'] = user.id
    session['name'] = user.name
    session['email'] = user.email
    session['role'] = user.role
    
    return jsonify({'success': True, 'role': user.role})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid email or password.'}), 401
        
    session['user_id'] = user.id
    session['name'] = user.name
    session['email'] = user.email
    session['role'] = user.role
    
    return jsonify({'success': True, 'role': user.role})

@app.route('/api/auth/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ==============================================================================
# MCQ TEST API ENDPOINTS
# ==============================================================================

@app.route('/api/questions/test', methods=['GET'])
@login_required
def get_test_questions():
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    limit = request.args.get('limit', default=10, type=int)
    bookmark_only = request.args.get('bookmarks', default='false') == 'true'
    
    query = Question.query
    
    if bookmark_only:
        # Get bookmarked questions for current user
        bookmarked_ids = [b.question_id for b in Bookmark.query.filter_by(user_id=session['user_id']).all()]
        if not bookmarked_ids:
            return jsonify({'questions': []})
        query = query.filter(Question.id.in_(bookmarked_ids))
    else:
        if category and category != 'All':
            query = query.filter(Question.category == category)
        if difficulty and difficulty != 'All':
            query = query.filter(Question.difficulty == difficulty)
            
    questions = query.all()
    # Randomize questions list
    random.shuffle(questions)
    questions = questions[:limit]
    
    # Gather user's bookmarks to tag them on the test view
    user_bookmarks = {b.question_id for b in Bookmark.query.filter_by(user_id=session['user_id']).all()}
    
    result_list = []
    for q in questions:
        q_dict = q.to_dict()
        q_dict['bookmarked'] = q.id in user_bookmarks
        # Do not send correct answer or explanation to the quiz taking view for security!
        del q_dict['correct_answer']
        if 'explanation' in q_dict:
            del q_dict['explanation']
        result_list.append(q_dict)
        
    return jsonify({'questions': result_list})

@app.route('/api/test/submit', methods=['POST'])
@login_required
def submit_test():
    data = request.get_json() or {}
    answers = data.get('answers', {}) # Dict of {question_id: selected_option}
    category = data.get('category', 'Mix')
    difficulty = data.get('difficulty', 'Mix')
    
    if not answers:
        # Edge case: submitted empty test
        return jsonify({'error': 'No answers submitted.'}), 400
        
    question_ids = [int(qid) for qid in answers.keys()]
    questions = Question.query.filter(Question.id.in_(question_ids)).all()
    questions_map = {q.id: q for q in questions}
    
    score = 0
    total_questions = len(question_ids)
    
    # Create Result row first to get result_id
    result = Result(
        user_id=session['user_id'],
        score=0,
        total_questions=total_questions,
        percentage=0.0,
        category=category,
        difficulty=difficulty
    )
    db.session.add(result)
    db.session.flush() # Flush to get auto-incremented id
    
    user_answers_to_add = []
    for qid_str, selected in answers.items():
        qid = int(qid_str)
        q = questions_map.get(qid)
        if not q:
            continue
            
        is_correct = (q.correct_answer == selected.upper())
        if is_correct:
            score += 1
            
        user_answers_to_add.append(
            UserAnswer(
                result_id=result.id,
                user_id=session['user_id'],
                question_id=qid,
                selected_answer=selected.upper(),
                is_correct=is_correct
            )
        )
        
    percentage = round((score / total_questions) * 100, 2) if total_questions > 0 else 0.0
    
    # Update Result
    result.score = score
    result.percentage = percentage
    
    for ua in user_answers_to_add:
        db.session.add(ua)
        
    db.session.commit()
    
    return jsonify({
        'success': True,
        'result_id': result.id,
        'score': score,
        'total': total_questions,
        'percentage': percentage,
        'pass_status': 'Pass' if percentage >= 50 else 'Fail'
    })


# ==============================================================================
# BOOKMARKS API
# ==============================================================================

@app.route('/api/bookmarks/toggle', methods=['POST'])
@login_required
def toggle_bookmark():
    data = request.get_json() or {}
    qid = data.get('question_id')
    if not qid:
        return jsonify({'error': 'Question ID is required.'}), 400
        
    bookmark = Bookmark.query.filter_by(user_id=session['user_id'], question_id=qid).first()
    if bookmark:
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({'success': True, 'bookmarked': False})
    else:
        new_bookmark = Bookmark(user_id=session['user_id'], question_id=qid)
        db.session.add(new_bookmark)
        db.session.commit()
        return jsonify({'success': True, 'bookmarked': True})


# ==============================================================================
# USER / PERFORMANCE ANALYTICS API
# ==============================================================================

@app.route('/api/student/analytics', methods=['GET'])
@login_required
def student_analytics():
    uid = session['user_id']
    
    # General stats
    total_tests = Result.query.filter_by(user_id=uid).count()
    if total_tests == 0:
        return jsonify({
            'total_tests': 0,
            'avg_percentage': 0,
            'strongest': 'N/A',
            'weakest': 'N/A',
            'history': [],
            'category_radar': {},
            'bookmarked_count': Bookmark.query.filter_by(user_id=uid).count()
        })
        
    avg_percentage = db.session.query(func.avg(Result.percentage)).filter(Result.user_id == uid).scalar() or 0.0
    
    # Category averages
    category_scores = db.session.query(
        Result.category,
        func.avg(Result.percentage).label('avg_score'),
        func.count(Result.id).label('test_count')
    ).filter(Result.user_id == uid).group_by(Result.category).all()
    
    category_radar = {cat: round(avg, 2) for cat, avg, count in category_scores if cat and cat != 'Mix'}
    
    # Calculate weakest / strongest
    sorted_categories = sorted(category_radar.items(), key=lambda x: x[1])
    weakest = sorted_categories[0][0] if sorted_categories else 'N/A'
    strongest = sorted_categories[-1][0] if sorted_categories else 'N/A'
    
    # Recent test history
    history = Result.query.filter_by(user_id=uid).order_by(Result.test_date.desc()).limit(10).all()
    history_list = [h.to_dict() for h in history]
    
    # Add date sorted ascending history for progress charts
    progress_history = Result.query.filter_by(user_id=uid).order_by(Result.test_date.asc()).limit(15).all()
    progress_list = [{'date': p.test_date.strftime('%m/%d %H:%M'), 'percentage': p.percentage} for p in progress_history]
    
    bookmarked_count = Bookmark.query.filter_by(user_id=uid).count()
    
    return jsonify({
        'total_tests': total_tests,
        'avg_percentage': round(avg_percentage, 2),
        'strongest': strongest,
        'weakest': weakest,
        'history': history_list,
        'progress': progress_list,
        'category_radar': category_radar,
        'bookmarked_count': bookmarked_count
    })

@app.route('/api/leaderboard', methods=['GET'])
@login_required
def leaderboard():
    # Rank users by their average percentage score
    leaders = db.session.query(
        User.name,
        func.avg(Result.percentage).label('avg_score'),
        func.count(Result.id).label('tests_taken')
    ).join(Result, Result.user_id == User.id)\
     .group_by(User.id)\
     .order_by(func.avg(Result.percentage).desc())\
     .limit(10).all()
     
    leader_list = [
        {'name': row.name, 'avg_score': round(row.avg_score, 2), 'tests_taken': row.tests_taken}
        for row in leaders
    ]
    return jsonify({'leaderboard': leader_list})

@app.route('/api/test/review-details/<int:result_id>', methods=['GET'])
@login_required
def review_details(result_id):
    res = Result.query.get_or_404(result_id)
    if session.get('role') != 'admin' and res.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    user_answers = UserAnswer.query.filter_by(result_id=result_id).all()
    
    details = []
    for ua in user_answers:
        q = Question.query.get(ua.question_id)
        if not q:
            continue
        details.append({
            'question': q.question,
            'option_a': q.option_a,
            'option_b': q.option_b,
            'option_c': q.option_c,
            'option_d': q.option_d,
            'selected': ua.selected_answer,
            'correct': q.correct_answer,
            'is_correct': ua.is_correct,
            'explanation': q.explanation
        })
        
    return jsonify({
        'category': res.category or 'Mix',
        'difficulty': res.difficulty or 'Mix',
        'score': res.score,
        'total': res.total_questions,
        'percentage': res.percentage,
        'answers': details
    })


# ==============================================================================
# ADMIN API ENDPOINTS (CRUD & ANALYTICS)
# ==============================================================================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    total_users = User.query.filter_by(role='student').count()
    total_questions = Question.query.count()
    avg_percentage = db.session.query(func.avg(Result.percentage)).scalar() or 0.0
    
    # Category question counts
    category_counts = db.session.query(
        Question.category, func.count(Question.id)
    ).group_by(Question.category).all()
    cat_breakdown = {cat: count for cat, count in category_counts}
    
    # Recent test activity
    recent_tests = db.session.query(
        Result.id,
        User.name.label('student_name'),
        Result.category,
        Result.score,
        Result.total_questions,
        Result.percentage,
        Result.test_date
    ).join(User, Result.user_id == User.id)\
     .order_by(Result.test_date.desc())\
     .limit(10).all()
     
    recent_activity = [
        {
            'result_id': row.id,
            'student_name': row.student_name,
            'category': row.category or 'Mix',
            'score': f"{row.score}/{row.total_questions}",
            'percentage': round(row.percentage, 2),
            'date': row.test_date.strftime('%Y-%m-%d %H:%M')
        }
        for row in recent_tests
    ]
    
    # Student scores summary (User rankings table)
    students_report = db.session.query(
        User.id,
        User.name,
        User.email,
        func.count(Result.id).label('tests_taken'),
        func.avg(Result.percentage).label('avg_score'),
        func.max(Result.percentage).label('max_score')
    ).join(Result, Result.user_id == User.id, isouter=True)\
     .filter(User.role == 'student')\
     .group_by(User.id)\
     .order_by(func.avg(Result.percentage).desc())\
     .all()
     
    students_list = [
        {
            'id': row.id,
            'name': row.name,
            'email': row.email,
            'tests_taken': row.tests_taken,
            'avg_score': round(row.avg_score or 0.0, 2),
            'max_score': round(row.max_score or 0.0, 2)
        }
        for row in students_report
    ]
    
    return jsonify({
        'total_users': total_users,
        'total_questions': total_questions,
        'avg_percentage': round(avg_percentage, 2),
        'category_breakdown': cat_breakdown,
        'recent_activity': recent_activity,
        'students_report': students_list
    })

@app.route('/api/admin/questions', methods=['GET'])
@admin_required
def admin_get_questions():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    difficulty = request.args.get('difficulty', '').strip()
    
    query = Question.query
    if search:
        query = query.filter(Question.question.like(f"%{search}%"))
    if category and category != 'All':
        query = query.filter(Question.category == category)
    if difficulty and difficulty != 'All':
        query = query.filter(Question.difficulty == difficulty)
        
    questions = query.order_by(Question.created_at.desc()).all()
    return jsonify({'questions': [q.to_dict() for q in questions]})

@app.route('/api/admin/questions', methods=['POST'])
@admin_required
def admin_add_question():
    data = request.get_json() or {}
    category = data.get('category', '').strip()
    difficulty = data.get('difficulty', '').strip()
    question_text = data.get('question', '').strip()
    op_a = data.get('option_a', '').strip()
    op_b = data.get('option_b', '').strip()
    op_c = data.get('option_c', '').strip()
    op_d = data.get('option_d', '').strip()
    correct = data.get('correct_answer', '').strip().upper()
    explanation = data.get('explanation', '').strip()
    
    if not (category and difficulty and question_text and op_a and op_b and op_c and op_d and correct in ['A', 'B', 'C', 'D']):
        return jsonify({'error': 'Invalid question parameters. All options and a correct answer (A-D) are required.'}), 400
        
    q = Question(
        category=category,
        difficulty=difficulty,
        question=question_text,
        option_a=op_a,
        option_b=op_b,
        option_c=op_c,
        option_d=op_d,
        correct_answer=correct,
        explanation=explanation
    )
    db.session.add(q)
    db.session.commit()
    return jsonify({'success': True, 'question': q.to_dict()})

@app.route('/api/admin/questions/<int:qid>', methods=['PUT', 'DELETE'])
@admin_required
def admin_manage_question(qid):
    q = Question.query.get_or_404(qid)
    
    if request.method == 'DELETE':
        db.session.delete(q)
        db.session.commit()
        return jsonify({'success': True})
        
    # Edit / Update
    data = request.get_json() or {}
    category = data.get('category', '').strip()
    difficulty = data.get('difficulty', '').strip()
    question_text = data.get('question', '').strip()
    op_a = data.get('option_a', '').strip()
    op_b = data.get('option_b', '').strip()
    op_c = data.get('option_c', '').strip()
    op_d = data.get('option_d', '').strip()
    correct = data.get('correct_answer', '').strip().upper()
    explanation = data.get('explanation', '').strip()
    
    if not (category and difficulty and question_text and op_a and op_b and op_c and op_d and correct in ['A', 'B', 'C', 'D']):
        return jsonify({'error': 'Invalid question parameters. All options and correct answer (A-D) are required.'}), 400
        
    q.category = category
    q.difficulty = difficulty
    q.question = question_text
    q.option_a = op_a
    q.option_b = op_b
    q.option_c = op_c
    q.option_d = op_d
    q.correct_answer = correct
    q.explanation = explanation
    
    db.session.commit()
    return jsonify({'success': True, 'question': q.to_dict()})

@app.route('/api/admin/import', methods=['POST'])
@admin_required
def admin_import_questions():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file.'}), 400
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files are allowed.'}), 400
        
    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        
        # Read header
        header = next(csv_input, None)
        if not header:
            return jsonify({'error': 'Empty CSV file.'}), 400
            
        # Expected Header: category,difficulty,question,option_a,option_b,option_c,option_d,correct_answer,explanation
        imported_count = 0
        for row in csv_input:
            if not row or len(row) < 8:
                continue
                
            category = row[0].strip()
            difficulty = row[1].strip()
            question_text = row[2].strip()
            op_a = row[3].strip()
            op_b = row[4].strip()
            op_c = row[5].strip()
            op_d = row[6].strip()
            ans = row[7].strip().upper()
            exp = row[8].strip() if len(row) > 8 else ''
            
            if not (category and difficulty and question_text and op_a and op_b and op_c and op_d and ans in ['A', 'B', 'C', 'D']):
                continue
                
            q = Question(
                category=category,
                difficulty=difficulty,
                question=question_text,
                option_a=op_a,
                option_b=op_b,
                option_c=op_c,
                option_d=op_d,
                correct_answer=ans,
                explanation=exp
            )
            db.session.add(q)
            imported_count += 1
            
        db.session.commit()
        return jsonify({'success': True, 'count': imported_count})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Failed to parse CSV: {str(e)}"}), 500

if __name__ == '__main__':
    # Default local dev running on port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
