import os
from flask import Flask, jsonify, request, make_response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_compress import Compress
from flask_cors import CORS
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import logging
from logging.handlers import RotatingFileHandler
import redis
from sqlalchemy import exc
from datetime import datetime, timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
import shutil
import functools
import time

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure file logging with rotation
os.makedirs('logs', exist_ok=True)
file_handler = RotatingFileHandler(
    'logs/app.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Sentry configuration for error tracking
sentry_sdk.init(
    dsn="",  # Will be configured if provided
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
socketio = SocketIO()
login_manager = LoginManager()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

# Enhanced security headers
@app.after_request
def add_security_headers(response):
    """
    Add security headers to the response.

    Args:
        response (flask.Response): The response object.

    Returns:
        flask.Response: The response object with added security headers.
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' https:; img-src 'self' data: https:; font-src 'self' https: data:;"
    return response

# Request timeout middleware
class TimeoutMiddleware:
    """
    Middleware to enforce request timeout.

    Args:
        app (flask.Flask): The Flask application.
        timeout (int): The timeout duration in seconds.
    """
    def __init__(self, app, timeout=30):
        self.app = app
        self.timeout = timeout

    def __call__(self, environ, start_response):
        from threading import Timer
        import thread

        timeout_handler = lambda: thread.interrupt_main()
        timer = Timer(self.timeout, timeout_handler)
        timer.start()
        try:
            return self.app(environ, start_response)
        finally:
            timer.cancel()

app.wsgi_app = TimeoutMiddleware(app.wsgi_app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration with improved error handling and connection pooling
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "echo": True,
}

# Enhanced CORS configuration
CORS(app, resources={
    r"/*": {
        "origins": os.environ.get("CORS_ORIGINS", "*"),
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

# Request timeout and security configurations
app.config['PERMANENT_SESSION_LIFETIME'] = 1800
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 43200
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Enhanced Redis configuration
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        cache_config = {
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': REDIS_URL,
            'CACHE_DEFAULT_TIMEOUT': 300,
            'CACHE_OPTIONS': {'socket_timeout': 5},
            'CACHE_KEY_PREFIX': 'eunica_',
            'CACHE_REDIS_HOST': redis_client.connection_pool.connection_kwargs['host'],
            'CACHE_REDIS_PORT': redis_client.connection_pool.connection_kwargs['port']
        }
        logger.info("Redis cache configured successfully")
    except redis.ConnectionError:
        logger.warning("Redis connection failed, falling back to simple cache")
        cache_config = {'CACHE_TYPE': 'simple'}
else:
    logger.info("No Redis URL configured, using simple cache")
    cache_config = {'CACHE_TYPE': 'simple'}

cache = Cache(app, config=cache_config)

# Enhanced rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window-elastic-expiry",
    headers_enabled=True
)

# Optimized compression settings
compress = Compress()
compress.init_app(app)
app.config['COMPRESS_ALGORITHM'] = 'gzip'
app.config['COMPRESS_LEVEL'] = 6
app.config['COMPRESS_MIN_SIZE'] = 500
app.config['COMPRESS_MIMETYPES'] = [
    'text/html', 'text/css', 'text/xml',
    'application/json', 'application/javascript',
    'text/javascript'
]

# File upload configurations with cleanup
UPLOAD_FOLDER = 'static/uploads'
TEMP_FOLDER = 'static/temp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMP_FOLDER'] = TEMP_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'pdf', 'doc', 'docx'}

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Configure database
db.init_app(app)

# Enhanced WebSocket configuration
socketio.init_app(app, 
    cors_allowed_origins=os.environ.get("CORS_ORIGINS", "*"),
    ping_timeout=10,
    ping_interval=5,
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1,
    reconnection_delay_max=5,
    logger=True,
    engineio_logger=True,
    async_mode='threading',
    cookie=True,
    message_queue=REDIS_URL if REDIS_URL else None
)

# Enhanced login manager configuration
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.session_protection = 'strong'
login_manager.refresh_view = 'login'
login_manager.needs_refresh_message = 'Session timed out, please login again'

# Cleanup tasks
def cleanup_temp_files():
    """
    Clean up temporary files older than 24 hours.
    """
    try:
        now = time.time()
        for root, dirs, files in os.walk(TEMP_FOLDER):
            for fname in files:
                path = os.path.join(root, fname)
                if os.path.getmtime(path) < now - 86400:  # 24 hours
                    os.remove(path)
        logger.info("Temporary files cleanup completed")
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")

def cleanup_expired_sessions():
    """
    Clean up expired sessions.
    """
    try:
        if REDIS_URL and redis_client:
            pattern = f"{cache_config['CACHE_KEY_PREFIX']}session:*"
            for key in redis_client.scan_iter(pattern):
                if redis_client.ttl(key) <= 0:
                    redis_client.delete(key)
        logger.info("Expired sessions cleanup completed")
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {str(e)}")

# Static file serving with caching
@app.route('/static/<path:filename>')
@cache.cached(timeout=43200)  # 12 hours
def serve_static(filename):
    """
    Serve static files with caching.

    Args:
        filename (str): The name of the file to serve.

    Returns:
        flask.Response: The response object with the static file.
    """
    response = make_response(send_from_directory('static', filename))
    response.headers['Cache-Control'] = 'public, max-age=43200'
    return response

# Schedule cleanup tasks
def schedule_cleanup():
    """
    Schedule cleanup tasks for temporary files and expired sessions.
    """
    cleanup_temp_files()
    cleanup_expired_sessions()

# Error handlers with improved logging
@app.errorhandler(404)
def not_found_error(error):
    """
    Handle 404 Not Found errors.

    Args:
        error (Exception): The error object.

    Returns:
        flask.Response: The response object with the error message.
    """
    logger.warning(f"404 error: {request.url}")
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 Internal Server errors.

    Args:
        error (Exception): The error object.

    Returns:
        flask.Response: The response object with the error message.
    """
    logger.error(f"500 error: {str(error)}")
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """
    Handle 429 Too Many Requests errors.

    Args:
        e (Exception): The error object.

    Returns:
        flask.Response: The response object with the error message.
    """
    logger.warning(f"Rate limit exceeded for {request.remote_addr}")
    return jsonify({'error': 'Rate limit exceeded'}), 429

# Health check endpoint
@app.route('/health')
@limiter.exempt
def health_check():
    """
    Perform a health check of the application.

    Returns:
        flask.Response: The response object with the health status.
    """
    try:
        db.session.execute('SELECT 1')
        db.session.remove()
        
        cache_status = False
        if REDIS_URL:
            try:
                cache_status = redis_client.ping()
            except:
                pass
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'cache': cache_status,
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat(),
            'uptime': time.time() - app.start_time
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

# Initialize application
try:
    with app.app_context():
        app.start_time = time.time()
        import models
        db.create_all()
        schedule_cleanup()
        logger.info('Application initialized successfully')
except Exception as e:
    logger.error(f"Failed to initialize application: {str(e)}")
    raise

from chat_socket import *
