import pymysql
from flask import Flask
from flask_bcrypt import Bcrypt
from config import Config
from database import db, User, Question
from urllib.parse import urlparse

def create_db_if_not_exists():
    uri = Config.SQLALCHEMY_DATABASE_URI
    if uri.startswith('mysql'):
        # Parse connection string
        result = urlparse(uri)
        username = result.username
        password = result.password
        hostname = result.hostname
        port = result.port or 3306
        # Remove leading slash to get DB name
        dbname = result.path.lstrip('/')
        
        print(f"Connecting to MySQL server at {hostname}:{port} to ensure database '{dbname}' exists...")
        try:
            conn = pymysql.connect(
                host=hostname,
                user=username,
                password=password,
                port=port
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {dbname}")
            print(f"Database '{dbname}' verified/created successfully.")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"\n[WARNING] Could not connect to MySQL to create database: {e}")
            print("Please make sure MySQL is running and credentials in config.py / environment are correct.")
            print("If you want to run with SQLite for quick testing, set environment variable USE_SQLITE=True.")
            print("Falling back to SQLite temporarily so initialization can proceed...")
            Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///placement_prep.db'

def initialize_database():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    bcrypt = Bcrypt(app)
    
    with app.app_context():
        # Create tables
        db.create_all()
        print("Database tables created.")
        
        # Verify if admin user exists
        admin_email = "seshasundharamoorthi2005@gmail.com"
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            hashed_pw = bcrypt.generate_password_hash("sesha@2005").decode('utf-8')
            admin = User(
                name="Sesha Admin",
                email=admin_email,
                password=hashed_pw,
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Default admin account created: {admin_email} / sesha@2005")
        else:
            print("Admin account already exists.")
            
        # Add sample questions if table is empty
        if Question.query.count() == 0:
            sample_questions = [
                # Aptitude
                Question(
                    category="Aptitude",
                    difficulty="Easy",
                    question="A train 120 m long passes a telegraph post in 6 seconds. Find the speed of the train in km/h.",
                    option_a="72 km/h",
                    option_b="60 km/h",
                    option_c="80 km/h",
                    option_d="90 km/h",
                    correct_answer="A",
                    explanation="Speed = Distance / Time = 120m / 6s = 20 m/s. To convert to km/h: 20 * 18/5 = 72 km/h."
                ),
                Question(
                    category="Aptitude",
                    difficulty="Medium",
                    question="A and B can do a piece of work in 12 days, B and C in 15 days, and C and A in 20 days. In how many days can A do the work alone?",
                    option_a="30 days",
                    option_b="40 days",
                    option_c="24 days",
                    option_d="36 days",
                    correct_answer="A",
                    explanation="Work rate of (A+B) = 1/12, (B+C) = 1/15, (C+A) = 1/20. Adding these, 2(A+B+C) = 1/12 + 1/15 + 1/20 = 12/60 = 1/5. Thus A+B+C = 1/10. A's rate = (A+B+C) - (B+C) = 1/10 - 1/15 = 1/30. So A alone takes 30 days."
                ),
                # Logical Reasoning
                Question(
                    category="Logical Reasoning",
                    difficulty="Easy",
                    question="Look at this series: 2, 1, (1/2), (1/4), ... What number should come next?",
                    option_a="1/3",
                    option_b="1/8",
                    option_c="2/8",
                    option_d="1/16",
                    correct_answer="B",
                    explanation="This is a simple division series; each number is one-half of the previous number. 1/4 divided by 2 is 1/8."
                ),
                Question(
                    category="Logical Reasoning",
                    difficulty="Medium",
                    question="If 'MEMBER' is coded as 'LDKADQ', how is 'NATION' coded in that language?",
                    option_a="MZSJNM",
                    option_b="MZSHNM",
                    option_c="NZSHNM",
                    option_d="MZSJNN",
                    correct_answer="B",
                    explanation="Each letter of MEMBER is shifted backward by 1 position (M->L, E->D, M->L, B->A, E->D, R->Q). Shifting NATION backward by 1: N->M, A->Z, T->S, I->H, O->N, N->M. So it is MZSHNM."
                ),
                # Verbal Ability
                Question(
                    category="Verbal Ability",
                    difficulty="Easy",
                    question="Choose the synonym of 'CANDID'.",
                    option_a="Honest",
                    option_b="Deceitful",
                    option_c="Secretive",
                    option_d="Vague",
                    correct_answer="A",
                    explanation="CANDID means truthful and straightforward; frank. Honest is the closest synonym."
                ),
                Question(
                    category="Verbal Ability",
                    difficulty="Medium",
                    question="Identify the grammatically correct sentence.",
                    option_a="Each of the students have finished their homework.",
                    option_b="Each of the students has finished their homework.",
                    option_c="Each of the students has finished his or her homework.",
                    option_d="Each of the students have finished his or her homework.",
                    correct_answer="C",
                    explanation="'Each' is a singular pronoun and requires a singular verb 'has' and singular possessives 'his or her'."
                ),
                # Programming
                Question(
                    category="Programming",
                    difficulty="Easy",
                    question="What is the output of print(2 ** 3) in Python?",
                    option_a="6",
                    option_b="8",
                    option_c="9",
                    option_d="16",
                    correct_answer="B",
                    explanation="** is the exponentiation operator in Python. 2 raised to power 3 is 8."
                ),
                Question(
                    category="Programming",
                    difficulty="Medium",
                    question="Which data structure uses the LIFO (Last In First Out) principle?",
                    option_a="Queue",
                    option_b="Stack",
                    option_c="Linked List",
                    option_d="Binary Tree",
                    correct_answer="B",
                    explanation="A Stack is a LIFO (Last In First Out) data structure, whereas a Queue is FIFO (First In First Out)."
                ),
                # Technical Subjects
                Question(
                    category="Technical Subjects",
                    difficulty="Medium",
                    question="Which layer of the OSI model is responsible for routing packets across networks?",
                    option_a="Transport Layer",
                    option_b="Network Layer",
                    option_c="Data Link Layer",
                    option_d="Physical Layer",
                    correct_answer="B",
                    explanation="The Network Layer (Layer 3) handles routing, IP addressing, and packet forwarding."
                ),
                Question(
                    category="Technical Subjects",
                    difficulty="Hard",
                    question="In database management systems, ACID properties ensure reliable transaction processing. What does 'I' stand for?",
                    option_a="Integration",
                    option_b="Isolation",
                    option_c="Consistency",
                    option_d="Independence",
                    correct_answer="B",
                    explanation="ACID stands for Atomicity, Consistency, Isolation, and Durability."
                )
            ]
            for q in sample_questions:
                db.session.add(q)
            db.session.commit()
            print(f"Added {len(sample_questions)} sample questions to database.")
            
if __name__ == '__main__':
    create_db_if_not_exists()
    initialize_database()
