#!/usr/bin/env python
"""
Database initialization script.
Usage: python init_db.py
"""

import os
from dotenv import load_dotenv
from app import create_app
from models import db

load_dotenv()

def init_database():
    """Initialize the database."""
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database initialized successfully!")


if __name__ == '__main__':
    init_database()
