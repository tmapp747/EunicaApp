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
    """
    Initialize static users in the database.

    This function creates static users in the database if they do not already exist.
    """
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
    """
    Handle graceful shutdown.

    This function handles the graceful shutdown of the application by cleaning up resources.

    Args:
        sig (int): The signal number.
        frame (frame object): The current stack frame.
    """
    logger.info('Shutting down gracefully...')
    try:
        db.session.remove()
        cache.clear()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    sys.exit(0)

def find_available_port(start_port, max_attempts=10):
    """
    Find an available port starting from start_port.

    This function attempts to find an available port starting from the specified start_port.

    Args:
        start_port (int): The starting port number.
        max_attempts (int): The maximum number of attempts to find an available port.

    Returns:
        int: The available port number.

    Raises:
        RuntimeError: If no available port is found after the specified number of attempts.
    """
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
    """
    Configure session handling.

    This function sets up the session handling configuration for the application.
    """
    from datetime import timedelta
    app.permanent_session_lifetime = timedelta(hours=24)
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

if __name__ == '__main__':
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup session handling
    setup_session_handler()
    
    try:
        # Initialize database and users
        with app.app_context():
            db.create_all()
            initialize_users()
        
        # Find available port
        port = find_available_port(5000)
        logger.info(f"Starting server on port {port}")
        
        # Run the application
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            use_reloader=True,
            log_output=True,
            debug=False  # Disable debug mode in production
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)
