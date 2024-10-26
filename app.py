import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
socketio = SocketIO()
login_manager = LoginManager()

# Create the app
app = Flask(__name__)

# Configure the app
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)
socketio.init_app(app, cors_allowed_origins="*")
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    import models  # noqa: F401
    import routes  # noqa: F401
    import socket_events  # noqa: F401
    db.create_all()
