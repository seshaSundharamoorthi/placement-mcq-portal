from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from config import Config
from database import db, User, Question, Result, UserAnswer, Bookmark
from functools import wraps
from sqlalchemy import func
from datetime import datetime, timedelta
import csv
import io
import random

app = Flask(__name__)
app.config.from_object(Config)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
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

def update_user_stats(user_id):
    user = User.query.get(user_id)
    if not user:
        return
        
    # Get total attempted, correct, wrong
    total_q = db.session.query(func.count(UserAnswer.id)).filter(UserAnswer.user_id == user_id).scalar() or 0
    correct_q = db.session.query(func.count(UserAnswer.id)).filter(UserAnswer.user_id == user_id, UserAnswer.is_correct == True).scalar() or 0
    wrong_q = total_q - correct_q
    
    user.total_attempted = total_q
    user.total_correct = correct_q
    user.total_wrong = wrong_q
    user.overall_percentage = round((correct_q / total_q) * 100, 2) if total_q > 0 else 0.0
    
    # Calculate category scores
    total_apt = db.session.query(func.count(UserAnswer.id))\
        .join(Question, UserAnswer.question_id == Question.id)\
        .filter(UserAnswer.user_id == user_id, Question.category == 'Aptitude').scalar() or 0
    correct_apt = db.session.query(func.count(UserAnswer.id))\
        .join(Question, UserAnswer.question_id == Question.id)\
        .filter(UserAnswer.user_id == user_id, Question.category == 'Aptitude', UserAnswer.is_correct == True).scalar() or 0
    user.aptitude_score = round((correct_apt / total_apt) * 100, 2) if total_apt > 0 else 0.0
    
    total_reasoning = db.session.query(func.count(UserAnswer.id))\
        .join(Question, UserAnswer.question_id == Question.id)\
        .filter(UserAnswer.user_id == user_id, Question.category == 'Logical Reasoning').scalar() or 0
    correct_reasoning = db.session.query(func.count(UserAnswer.id))\
        .join(Question, UserAnswer.question_id == Question.id)\
        .filter(UserAnswer.user_id == user_id, Question.category == 'Logical Reasoning', UserAnswer.is_correct == True).scalar() or 0
    user.reasoning_score = round((correct_reasoning / total_reasoning) * 100, 2) if total_reasoning > 0 else 0.0
    
    total_prog = db.session.query(func.count(UserAnswer.id))\
        .join(Question, UserAnswer.question_id == Question.id)\
        .filter(UserAnswer.user_id == user_id, Question.category == 'Programming').scalar() or 0
    correct_prog = db.session.query(func.count(UserAnswer.id))\
        .join(Question, UserAnswer.question_id == Question.id)\
        .filter(UserAnswer.user_id == user_id, Question.category == 'Programming', UserAnswer.is_correct == True).scalar() or 0
    user.programming_score = round((correct_prog / total_prog) * 100, 2) if total_prog > 0 else 0.0
    
    # Calculate programming language-wise scores
    languages = ['Python', 'Java', 'C', 'C++', 'JavaScript']
    lang_scores = {}
    for lang in languages:
        total_lang = db.session.query(func.count(UserAnswer.id))\
            .join(Question, UserAnswer.question_id == Question.id)\
            .filter(UserAnswer.user_id == user_id, Question.category == 'Programming', Question.subcategory == lang).scalar() or 0
        correct_lang = db.session.query(func.count(UserAnswer.id))\
            .join(Question, UserAnswer.question_id == Question.id)\
            .filter(UserAnswer.user_id == user_id, Question.category == 'Programming', Question.subcategory == lang, UserAnswer.is_correct == True).scalar() or 0
        lang_scores[lang] = round((correct_lang / total_lang) * 100, 2) if total_lang > 0 else 0.0
        
    user.python_score = lang_scores['Python']
    user.java_score = lang_scores['Java']
    user.c_score = lang_scores['C']
    user.cpp_score = lang_scores['C++']
    user.javascript_score = lang_scores['JavaScript']
    
    db.session.commit()

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
    return render_template('test_taking.html')

@app.route('/test/result/<int:result_id>')
@login_required
def test_result(result_id):
    res = Result.query.get_or_404(result_id)
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
        
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email is already registered.'}), 400
        
    if email == "seshasundharamoorthi2005@gmail.com":
        return jsonify({'error': 'This email is reserved for Admin.'}), 403
        
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(name=name, email=email, password=hashed_pw, role='student', last_login=datetime.utcnow())
    db.session.add(user)
    db.session.commit()
    
    # Enable persistent session cookie
    session.permanent = True
    session['user_id'] = user.id
    session['name'] = user.name
    session['email'] = user.email
    session['role'] = user.role
    
    # Compute initial stats
    update_user_stats(user.id)
    
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
        
    # Update last login time
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Enable persistent session cookie
    session.permanent = True
    session['user_id'] = user.id
    session['name'] = user.name
    session['email'] = user.email
    session['role'] = user.role
    
    # Update stats just in case
    update_user_stats(user.id)
    
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
    subcategory = request.args.get('subcategory')
    difficulty = request.args.get('difficulty')
    limit = request.args.get('limit', default=10, type=int)
    bookmark_only = request.args.get('bookmarks', default='false') == 'true'
    
    query = Question.query
    
    if bookmark_only:
        bookmarked_ids = [b.question_id for b in Bookmark.query.filter_by(user_id=session['user_id']).all()]
        if not bookmarked_ids:
            return jsonify({'questions': []})
        query = query.filter(Question.id.in_(bookmarked_ids))
    else:
        if category and category != 'All':
            query = query.filter(Question.category == category)
            if category == 'Programming' and subcategory and subcategory != 'All':
                query = query.filter(Question.subcategory == subcategory)
        if difficulty and difficulty != 'All':
            query = query.filter(Question.difficulty == difficulty)
            
    questions = query.all()
    random.shuffle(questions)
    questions = questions[:limit]
    
    user_bookmarks = {b.question_id for b in Bookmark.query.filter_by(user_id=session['user_id']).all()}
    
    result_list = []
    for q in questions:
        q_dict = q.to_dict()
        q_dict['bookmarked'] = q.id in user_bookmarks
        del q_dict['correct_answer']
        if 'explanation' in q_dict:
            del q_dict['explanation']
        result_list.append(q_dict)
        
    return jsonify({'questions': result_list})

@app.route('/api/test/submit', methods=['POST'])
@login_required
def submit_test():
    data = request.get_json() or {}
    answers = data.get('answers', {})
    category = data.get('category', 'Mix')
    subcategory = data.get('subcategory', '')
    difficulty = data.get('difficulty', 'Mix')
    
    if not answers:
        return jsonify({'error': 'No answers submitted.'}), 400
        
    question_ids = [int(qid) for qid in answers.keys()]
    questions = Question.query.filter(Question.id.in_(question_ids)).all()
    questions_map = {q.id: q for q in questions}
    
    score = 0
    total_questions = len(question_ids)
    
    result = Result(
        user_id=session['user_id'],
        score=0,
        total_questions=total_questions,
        percentage=0.0,
        category=category,
        subcategory=subcategory or None,
        difficulty=difficulty
    )
    db.session.add(result)
    db.session.flush()
    
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
    result.score = score
    result.percentage = percentage
    
    for ua in user_answers_to_add:
        db.session.add(ua)
        
    db.session.commit()
    
    # Recalculate persistent statistics
    update_user_stats(session['user_id'])
    
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
    user = User.query.get(uid)
    
    # General stats
    total_tests = Result.query.filter_by(user_id=uid).count()
    
    # Recent test history
    history = Result.query.filter_by(user_id=uid).order_by(Result.test_date.desc()).limit(10).all()
    history_list = [h.to_dict() for h in history]
    
    # Add date sorted ascending history for progress charts
    progress_history = Result.query.filter_by(user_id=uid).order_by(Result.test_date.asc()).limit(15).all()
    progress_list = [{'date': p.test_date.strftime('%m/%d %H:%M'), 'percentage': p.percentage} for p in progress_history]
    
    bookmarked_count = Bookmark.query.filter_by(user_id=uid).count()
    
    category_radar = {
        'Aptitude': user.aptitude_score,
        'Logical Reasoning': user.reasoning_score,
        'Programming': user.programming_score
    }
    
    return jsonify({
        'total_tests': total_tests,
        'avg_percentage': user.overall_percentage,
        'strongest': max(category_radar, key=category_radar.get) if total_tests > 0 else 'N/A',
        'weakest': min(category_radar, key=category_radar.get) if total_tests > 0 else 'N/A',
        'history': history_list,
        'progress': progress_list,
        'category_radar': category_radar,
        'bookmarked_count': bookmarked_count,
        'user_details': user.to_dict()
    })

@app.route('/api/leaderboard', methods=['GET'])
@login_required
def leaderboard():
    leaders = User.query.filter_by(role='student')\
        .order_by(User.overall_percentage.desc())\
        .limit(10).all()
     
    leader_list = [
        {'name': u.name, 'avg_score': u.overall_percentage, 'tests_taken': Result.query.filter_by(user_id=u.id).count()}
        for u in leaders
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
        'subcategory': res.subcategory or '',
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
    avg_percentage = db.session.query(func.avg(User.overall_percentage)).filter(User.role == 'student').scalar() or 0.0
    
    category_counts = db.session.query(
        Question.category, func.count(Question.id)
    ).group_by(Question.category).all()
    cat_breakdown = {cat: count for cat, count in category_counts}
    
    recent_tests = db.session.query(
        Result.id,
        User.name.label('student_name'),
        Result.category,
        Result.subcategory,
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
            'category': f"{row.category} ({row.subcategory})" if row.subcategory else (row.category or 'Mix'),
            'score': f"{row.score}/{row.total_questions}",
            'percentage': round(row.percentage, 2),
            'date': row.test_date.strftime('%Y-%m-%d %H:%M')
        }
        for row in recent_tests
    ]
    
    students_report = User.query.filter_by(role='student').all()
    students_list = [u.to_dict() for u in students_report]
    
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
    subcategory = data.get('subcategory', '').strip() or None
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
        
    if category == 'Programming':
        if not subcategory or subcategory not in ['Python', 'Java', 'C', 'C++', 'JavaScript']:
            return jsonify({'error': 'For Programming category, a valid subcategory (Python, Java, C, C++, JavaScript) is required.'}), 400
    else:
        subcategory = None
        
    existing_q = Question.query.filter(
        Question.question == question_text,
        Question.category == category
    ).first()
    if existing_q:
        return jsonify({'error': 'Question already exists in this category.'}), 400

    q = Question(
        category=category,
        subcategory=subcategory,
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
        
    data = request.get_json() or {}
    category = data.get('category', '').strip()
    subcategory = data.get('subcategory', '').strip() or None
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
        
    if category == 'Programming':
        if not subcategory or subcategory not in ['Python', 'Java', 'C', 'C++', 'JavaScript']:
            return jsonify({'error': 'For Programming category, a valid subcategory (Python, Java, C, C++, JavaScript) is required.'}), 400
    else:
        subcategory = None
        
    q.category = category
    q.subcategory = subcategory
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
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        csv_input = csv.reader(stream)
        
        header_row = next(csv_input, None)
        if not header_row:
            return jsonify({'error': 'Empty CSV file.'}), 400
            
        header = [h.strip().lower() for h in header_row]
        
        try:
            cat_idx = header.index('category')
            diff_idx = header.index('difficulty')
            q_idx = header.index('question')
            a_idx = header.index('option_a')
            b_idx = header.index('option_b')
            c_idx = header.index('option_c')
            d_idx = header.index('option_d')
            ans_idx = header.index('correct_answer')
        except ValueError as e:
            return jsonify({'error': f"Missing required column in CSV header: {str(e)}"}), 400
            
        subcat_idx = header.index('subcategory') if 'subcategory' in header else -1
        exp_idx = header.index('explanation') if 'explanation' in header else -1
        
        imported_count = 0
        for row in csv_input:
            if not row or len(row) < len(header):
                continue
                
            category = row[cat_idx].strip()
            difficulty = row[diff_idx].strip()
            question_text = row[q_idx].strip()
            op_a = row[a_idx].strip()
            op_b = row[b_idx].strip()
            op_c = row[c_idx].strip()
            op_d = row[d_idx].strip()
            ans = row[ans_idx].strip().upper()
            
            subcategory = row[subcat_idx].strip() if subcat_idx != -1 else ''
            explanation = row[exp_idx].strip() if exp_idx != -1 else ''
            
            if not (category and difficulty and question_text and op_a and op_b and op_c and op_d and ans in ['A', 'B', 'C', 'D']):
                continue
            
            if category == 'Programming':
                if not subcategory or subcategory == '':
                    q_lower = question_text.lower()
                    if 'python' in q_lower: subcategory = 'Python'
                    elif 'java' in q_lower and 'javascript' not in q_lower: subcategory = 'Java'
                    elif 'javascript' in q_lower or 'js' in q_lower: subcategory = 'JavaScript'
                    elif 'c++' in q_lower or 'cpp' in q_lower: subcategory = 'C++'
                    else: subcategory = 'C'
            else:
                subcategory = None
                
            # Check for duplicate
            existing_q = Question.query.filter(
                Question.question == question_text,
                Question.category == category
            ).first()
            if existing_q:
                continue
                
            q = Question(
                category=category,
                subcategory=subcategory,
                difficulty=difficulty,
                question=question_text,
                option_a=op_a,
                option_b=op_b,
                option_c=op_c,
                option_d=op_d,
                correct_answer=ans,
                explanation=explanation
            )
            db.session.add(q)
            imported_count += 1
            
        db.session.commit()
        return jsonify({'success': True, 'count': imported_count})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Failed to parse CSV: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
