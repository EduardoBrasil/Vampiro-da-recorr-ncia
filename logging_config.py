import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(app):
    """Configure structured logging for the application."""
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Remove default Flask logger handlers
    app.logger.handlers = []
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)
    app.logger.addHandler(console_handler)
    
    # File handler (rotating)
    log_file = os.path.join(logs_dir, 'app.log')
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    app.logger.addHandler(file_handler)
    
    # Error file handler
    error_log_file = os.path.join(logs_dir, 'error.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    app.logger.addHandler(error_handler)
    
    # Set app logger level
    app.logger.setLevel(logging.DEBUG)
    
    # Log startup
    app.logger.info(f"Application started in {os.environ.get('FLASK_ENV', 'development')} mode")
