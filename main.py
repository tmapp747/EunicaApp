from app import app, socketio, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from models import User, Message, ChatRoom
from werkzeug.utils import secure_filename
import os
import uuid

STATIC_USERS = {
    'Bossm': 'Bossm143',
    'Jam': 'Jam143',
    'Buboy': 'Buboy143',
    'Ruel': 'Ruel143',
    'Aira': 'Aira143'
}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file):
    if not file:
        return None, None
        
    filename = secure_filename(file.filename)
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join('uploads', unique_filename)
    absolute_path = os.path.join('static', file_path)
    
    # Ensure upload directory exists
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
    
    file.save(absolute_path)
    return file_path, filename

def initialize_users():
    with app.app_context():
        # Only add users if they don't exist
        for username, password in STATIC_USERS.items():
            if not User.query.filter_by(username=username).first():
                user = User()
                user.username = username
                user.set_password(password)
                db.session.add(user)
        db.session.commit()

def get_or_create_chat(user1, user2):
    # Check if a direct chat between these users already exists
    chat = ChatRoom.query.filter(
        ChatRoom.is_group == False,
        ChatRoom.users.contains(user1),
        ChatRoom.users.contains(user2)
    ).first()
    
    if not chat:
        # Set chat name as partner's username
        chat = ChatRoom()
        chat.name = user2.username if user1 == current_user else user1.username
        chat.is_group = False
        chat.users.append(user1)
        chat.users.append(user2)
        db.session.add(chat)
        db.session.commit()
    
    return chat

@app.route('/')
@login_required
def index():
    return redirect(url_for('chat'))

@app.route('/chat')
@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id=None):
    users = User.query.all()
    active_chat = None
    chat_partner = None
    messages = []

    if user_id:
        chat_partner = User.query.get_or_404(user_id)
        active_chat = get_or_create_chat(current_user, chat_partner)
        messages = Message.query.filter_by(chatroom_id=active_chat.id).order_by(Message.timestamp.asc()).all()

    return render_template('chat.html', users=users, active_chat=active_chat, chat_partner=chat_partner, messages=messages)

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
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
        
    if file and not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
        
    # Handle file upload if present
    file_path = None
    file_name = None
    message_type = 'text'
    
    if file:
        file_path, file_name = save_file(file)
        if file_path:
            message_type = 'image' if file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')) else 'file'
    
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
