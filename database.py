from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'admin' or 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Progress & Analytics Columns
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    total_attempted = db.Column(db.Integer, default=0, nullable=False)
    total_correct = db.Column(db.Integer, default=0, nullable=False)
    total_wrong = db.Column(db.Integer, default=0, nullable=False)
    overall_percentage = db.Column(db.Float, default=0.0, nullable=False)
    
    # Category average scores (out of 100)
    aptitude_score = db.Column(db.Float, default=0.0, nullable=False)
    reasoning_score = db.Column(db.Float, default=0.0, nullable=False)
    programming_score = db.Column(db.Float, default=0.0, nullable=False)
    
    # Programming subcategory average scores (out of 100)
    python_score = db.Column(db.Float, default=0.0, nullable=False)
    java_score = db.Column(db.Float, default=0.0, nullable=False)
    c_score = db.Column(db.Float, default=0.0, nullable=False)
    cpp_score = db.Column(db.Float, default=0.0, nullable=False)
    javascript_score = db.Column(db.Float, default=0.0, nullable=False)
    
    results = db.relationship('Result', backref='user', lazy=True, cascade="all, delete-orphan")
    bookmarks = db.relationship('Bookmark', backref='user', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None,
            'total_attempted': self.total_attempted,
            'total_correct': self.total_correct,
            'total_wrong': self.total_wrong,
            'overall_percentage': self.overall_percentage,
            'aptitude_score': self.aptitude_score,
            'reasoning_score': self.reasoning_score,
            'programming_score': self.programming_score,
            'python_score': self.python_score,
            'java_score': self.java_score,
            'c_score': self.c_score,
            'cpp_score': self.cpp_score,
            'javascript_score': self.javascript_score
        }

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # 'Aptitude', 'Logical Reasoning', 'Verbal Ability', 'Programming', 'Technical Subjects'
    subcategory = db.Column(db.String(50), nullable=True)  # For Programming: 'Python', 'Java', 'C', 'C++', 'JavaScript'
    difficulty = db.Column(db.String(20), nullable=False)  # 'Easy', 'Medium', 'Hard'
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', 'D'
    explanation = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_answers = db.relationship('UserAnswer', backref='question', lazy=True, cascade="all, delete-orphan")
    bookmarks = db.relationship('Bookmark', backref='question', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'subcategory': self.subcategory or '',
            'difficulty': self.difficulty,
            'question': self.question,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'correct_answer': self.correct_answer,
            'explanation': self.explanation
        }

class Result(db.Model):
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    test_date = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=True)
    subcategory = db.Column(db.String(50), nullable=True)  # For language-wise scores
    difficulty = db.Column(db.String(20), nullable=True)
    
    answers = db.relationship('UserAnswer', backref='result', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'score': self.score,
            'total_questions': self.total_questions,
            'percentage': self.percentage,
            'test_date': self.test_date.strftime('%Y-%m-%d %H:%M:%S'),
            'category': self.category or 'Mix',
            'subcategory': self.subcategory or '',
            'difficulty': self.difficulty or 'Mix'
        }

class UserAnswer(db.Model):
    __tablename__ = 'user_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('results.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    selected_answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', 'D'
    is_correct = db.Column(db.Boolean, nullable=False)

class Bookmark(db.Model):
    __tablename__ = 'bookmarks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'question_id', name='_user_question_uc'),)
