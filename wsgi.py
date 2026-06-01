"""
WSGI entry point for production deployment with Gunicorn.
Usage: gunicorn --config gunicorn_config.py wsgi:app
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env vars
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "production"))

if __name__ == "__main__":
    app.run()
