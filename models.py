from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Index

class User(UserMixin, db.Model):
    """
    Represents a user in the application.

    Attributes:
        id (int): The unique identifier for the user.
        username (str): The username of the user.
        password_hash (str): The hashed password of the user.
        messages (list): The list of messages sent by the user.
        chatrooms (list): The list of chat rooms the user is part of.
    """
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    messages = db.relationship('Message', backref='sender', lazy='dynamic')
    chatrooms = db.relationship('ChatRoom', secondary='user_chatroom', back_populates='users')

    def set_password(self, password):
        """
        Set the password for the user.

        Args:
            password (str): The password to be hashed and set.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Check if the provided password matches the stored hashed password.

        Args:
            password (str): The password to be checked.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return check_password_hash(self.password_hash, password)

# Association table for User-ChatRoom many-to-many relationship
user_chatroom = db.Table('user_chatroom',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    db.Column('chatroom_id', db.Integer, db.ForeignKey('chat_room.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_user_chatroom', 'user_id', 'chatroom_id')
)

class ChatRoom(db.Model):
    """
    Represents a chat room in the application.

    Attributes:
        id (int): The unique identifier for the chat room.
        name (str): The name of the chat room.
        is_group (bool): Indicates if the chat room is a group chat.
        created_at (datetime): The timestamp when the chat room was created.
        users (list): The list of users in the chat room.
        messages (list): The list of messages in the chat room.
    """
    __tablename__ = 'chat_room'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    is_group = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    users = db.relationship('User', secondary='user_chatroom', back_populates='chatrooms')
    messages = db.relationship('Message', backref='chatroom', lazy='dynamic',
                             cascade='all, delete-orphan')

class Message(db.Model):
    """
    Represents a message in the application.

    Attributes:
        id (int): The unique identifier for the message.
        content (str): The content of the message.
        message_type (str): The type of the message (e.g., text, image, file, voice).
        file_path (str): The file path of the attached file, if any.
        file_name (str): The file name of the attached file, if any.
        timestamp (datetime): The timestamp when the message was sent.
        sender_id (int): The ID of the user who sent the message.
        chatroom_id (int): The ID of the chat room where the message was sent.
    """
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000))
    message_type = db.Column(db.String(20), default='text')  # text, image, file, voice
    file_path = db.Column(db.String(255))
    file_name = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    chatroom_id = db.Column(db.Integer, db.ForeignKey('chat_room.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        Index('idx_message_chatroom_timestamp', 'chatroom_id', 'timestamp'),
    )

@login_manager.user_loader
def load_user(id):
    """
    Load a user by their ID.

    Args:
        id (int): The ID of the user to be loaded.

    Returns:
        User: The user object if found, None otherwise.
    """
    return User.query.get(int(id))
