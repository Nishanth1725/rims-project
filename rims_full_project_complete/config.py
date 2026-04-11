import os
class Config:
    # PostgreSQL connection string format: postgresql://username:password@host:port/database
    # Default to PostgreSQL (can be overridden by DATABASE_URL environment variable)
    # Updated default to match your local PostgreSQL credentials: username=postgres, password=1725
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:1725@localhost:5432/da')
    
    # If DATABASE_URL doesn't start with postgresql://, use SQLite
    if not DATABASE_URL.startswith('postgresql://') and not DATABASE_URL.startswith('postgresql+psycopg2://'):
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Ensure psycopg2 driver is used for PostgreSQL
        if DATABASE_URL.startswith('postgresql://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
        else:
            SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # Set to True for SQL query debugging - ENABLED TO SEE QUERIES
