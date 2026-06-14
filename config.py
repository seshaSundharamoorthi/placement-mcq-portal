import os

class Config:
    # Flask Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'placement-prep-portal-secret-key-12345')
    
    # Database Configuration
    # Prioritize MySQL environment variables, fall back to SQLite for easy development
    DB_USER = os.environ.get('MYSQL_USER', 'root')
    DB_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    DB_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    DB_PORT = os.environ.get('MYSQL_PORT', '3306')
    DB_NAME = os.environ.get('MYSQL_DB', 'placement_prep')
    
    # If environment says use MySQL, or if we have user credentials
    # Check if a custom MySQL URI is provided directly
    MYSQL_URI = os.environ.get('DATABASE_URL')
    
    if MYSQL_URI:
        SQLALCHEMY_DATABASE_URI = MYSQL_URI
    elif os.environ.get('USE_SQLITE') == 'True' or not DB_PASSWORD and DB_USER == 'root' and os.environ.get('MYSQL_HOST') is None:
        # If no host is configured and password is empty, default to SQLite for testing
        # BUT prioritize MySQL if host is defined.
        SQLALCHEMY_DATABASE_URI = 'sqlite:///placement_prep.db'
    else:
        # Construct MySQL connection string
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
