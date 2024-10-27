from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    messages = db.relationship('Message', backref='sender', lazy='dynamic')
    chatrooms = db.relationship('ChatRoom', secondary='user_chatroom', back_populates='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    is_group = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    users = db.relationship('User', secondary='user_chatroom', back_populates='chatrooms')
    messages = db.relationship('Message', backref='chatroom', lazy='dynamic')

# Association table for User-ChatRoom many-to-many relationship
user_chatroom = db.Table('user_chatroom',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('chatroom_id', db.Integer, db.ForeignKey('chat_room.id'), primary_key=True)
)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, image, file, voice
    file_path = db.Column(db.String(255))
    file_name = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chatroom_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
