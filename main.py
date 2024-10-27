from app import app, socketio, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from models import User, Message, ChatRoom
from werkzeug.utils import secure_filename
import os
import uuid
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_USERS = {
    'Bossm': 'Bossm143',
    'Jam': 'Jam143',
    'Buboy': 'Buboy143',
    'Ruel': 'Ruel143',
    'Aira': 'Aira143'
}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file):
    try:
        if not file:
            return None, None
            
        if not allowed_file(file.filename):
            raise ValueError("File type not allowed")
            
        if file.content_length and file.content_length > MAX_FILE_SIZE:
            raise ValueError("File size exceeds maximum limit")
            
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Create year/month based directory structure
        today = datetime.now()
        relative_path = os.path.join('uploads', str(today.year), str(today.month))
        file_path = os.path.join('static', relative_path)
        
        # Ensure upload directory exists
        os.makedirs(file_path, exist_ok=True)
        
        # Save file
        file_full_path = os.path.join(file_path, unique_filename)
        file.save(file_full_path)
        
        # Return relative path from static directory
        return os.path.join(relative_path, unique_filename), filename
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise

def initialize_users():
    try:
        with app.app_context():
            for username, password in STATIC_USERS.items():
                if not User.query.filter_by(username=username).first():
                    user = User()
                    user.username = username
                    user.set_password(password)
                    db.session.add(user)
            db.session.commit()
    except Exception as e:
        logger.error(f"Error initializing users: {str(e)}")
        db.session.rollback()

def get_or_create_chat(user1, user2):
    try:
        chat = ChatRoom.query.filter(
            ChatRoom.is_group == False,
            ChatRoom.users.contains(user1),
            ChatRoom.users.contains(user2)
        ).first()
        
        if not chat:
            chat = ChatRoom()
            chat.name = user2.username if user1 == current_user else user1.username
            chat.is_group = False
            chat.users.append(user1)
            chat.users.append(user2)
            db.session.add(chat)
            db.session.commit()
        
        return chat
        
    except Exception as e:
        logger.error(f"Error getting/creating chat: {str(e)}")
        db.session.rollback()
        raise

@app.route('/')
@login_required
def index():
    return redirect(url_for('chat'))

@app.route('/chat')
@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id=None):
    try:
        users = User.query.all()
        active_chat = None
        chat_partner = None
        messages = []

        if user_id:
            chat_partner = User.query.get_or_404(user_id)
            active_chat = get_or_create_chat(current_user, chat_partner)
            messages = Message.query.filter_by(chatroom_id=active_chat.id).order_by(Message.timestamp.asc()).all()

        return render_template('chat.html', users=users, active_chat=active_chat, chat_partner=chat_partner, messages=messages)
        
    except Exception as e:
        logger.error(f"Error in chat route: {str(e)}")
        flash("An error occurred. Please try again.")
        return redirect(url_for('index'))

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    try:
        chat_id = request.form.get('chat_id')
        if not chat_id:
            return jsonify({'error': 'No chat ID provided'}), 400
            
        chatroom = ChatRoom.query.get(chat_id)
        if not chatroom or current_user not in chatroom.users:
            return jsonify({'error': 'Invalid chat room'}), 403
            
        message_text = request.form.get('message', '').strip()
        file = request.files.get('file')
        
        if not message_text and not file:
            return jsonify({'error': 'No content provided'}), 400
            
        # Handle file upload if present
        file_path = None
        file_name = None
        message_type = 'text'
        
        if file:
            try:
                file_path, file_name = save_file(file)
                if file_path:
                    message_type = 'image' if file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')) else 'file'
            except ValueError as ve:
                return jsonify({'error': str(ve)}), 400
            except Exception as e:
                logger.error(f"File upload error: {str(e)}")
                return jsonify({'error': 'File upload failed'}), 500
        
        # Create message
        message = Message(
            content=message_text if message_text else '',
            message_type=message_type,
            file_path=file_path,
            file_name=file_name,
            sender_id=current_user.id,
            chatroom_id=chat_id
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Emit socket event
        socketio.emit('new_message', {
            'message': message.content,
            'message_type': message_type,
            'file_path': url_for('static', filename=file_path) if file_path else None,
            'file_name': file_name,
            'username': current_user.username,
            'sender_id': current_user.id,
            'timestamp': message.timestamp.strftime('%H:%M')
        }, room=str(chat_id))
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to send message'}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username not in STATIC_USERS:
            flash('Invalid username')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# Initialize static users
initialize_users()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=True, log_output=True)
