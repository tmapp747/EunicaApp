import os
from app import app, socketio, db, cache, limiter
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from models import User, Message, ChatRoom
from werkzeug.utils import secure_filename
import uuid
import logging
import signal
import sys
from datetime import datetime
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Static users for development
STATIC_USERS = {
    'Bossm': 'Bossm143',
    'Jam': 'Jam143',
    'Buboy': 'Buboy143',
    'Ruel': 'Ruel143',
    'Aira': 'Aira143'
}

def initialize_users():
    """Initialize static users in the database"""
    try:
        with app.app_context():
            for username, password in STATIC_USERS.items():
                if not User.query.filter_by(username=username).first():
                    user = User()
                    user.username = username
                    user.password_hash = generate_password_hash(password)
                    db.session.add(user)
            db.session.commit()
            logger.info("Static users initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing users: {str(e)}")
        db.session.rollback()
        raise

def signal_handler(sig, frame):
    """Handle graceful shutdown"""
    logger.info('Shutting down gracefully...')
    try:
        db.session.remove()
        cache.clear()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    sys.exit(0)

def find_available_port(start_port, max_attempts=10):
    """Find an available port starting from start_port"""
    import socket
    port = start_port
    while max_attempts > 0:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            port += 1
            max_attempts -= 1
    raise RuntimeError("Could not find an available port")

def setup_session_handler():
    """Configure session handling"""
    from datetime import timedelta
    app.permanent_session_lifetime = timedelta(hours=24)
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

def initialize_app():
    """Initialize the Flask application with all required setup"""
    try:
        # Create necessary directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Setup session handling
        setup_session_handler()

        # Initialize extensions
        with app.app_context():
            db.create_all()
            initialize_users()
            cache.clear()  # Clear cache on startup

        return True
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        return False

if __name__ == '__main__':
    if initialize_app():
        try:
            port = find_available_port(5000)
            logger.info(f"Starting server on port {port}")
            
            socketio.run(
                app,
                host='0.0.0.0',
                port=port,
                use_reloader=True,
                log_output=True,
                debug=os.environ.get('FLASK_ENV') == 'development'
            )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)
