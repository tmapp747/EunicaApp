import os
from app import app, socketio, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from models import User, Message, ChatRoom
from werkzeug.utils import secure_filename
import uuid
import logging
from datetime import datetime
from sqlalchemy import or_

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
        groups = ChatRoom.query.filter(
            ChatRoom.is_group == True,
            ChatRoom.users.contains(current_user)
        ).all()

        if user_id:
            chat_partner = User.query.get_or_404(user_id)
            active_chat = get_or_create_chat(current_user, chat_partner)
            messages = Message.query.filter_by(chatroom_id=active_chat.id).order_by(Message.timestamp.asc()).all()

        return render_template('chat.html', users=users, active_chat=active_chat, 
                            chat_partner=chat_partner, messages=messages, groups=groups)
        
    except Exception as e:
        logger.error(f"Error in chat route: {str(e)}")
        flash("An error occurred. Please try again.")
        return redirect(url_for('index'))

@app.route('/chat/group/<int:group_id>')
@login_required
def chat_group(group_id):
    try:
        group = ChatRoom.query.get_or_404(group_id)
        if not current_user in group.users:
            flash("You don't have access to this group")
            return redirect(url_for('chat'))
            
        users = User.query.all()
        groups = ChatRoom.query.filter(
            ChatRoom.is_group == True,
            ChatRoom.users.contains(current_user)
        ).all()
        messages = Message.query.filter_by(chatroom_id=group_id).order_by(Message.timestamp.asc()).all()
        
        return render_template('chat.html', users=users, active_chat=group,
                            messages=messages, groups=groups)
                            
    except Exception as e:
        logger.error(f"Error in group chat route: {str(e)}")
        flash("An error occurred. Please try again.")
        return redirect(url_for('chat'))

@app.route('/create_group', methods=['POST'])
@login_required
def create_group():
    try:
        name = request.form.get('name', '').strip()
        member_ids = request.form.getlist('members')
        
        if not name:
            return jsonify({'error': 'Group name is required'}), 400
            
        if not member_ids:
            return jsonify({'error': 'Select at least one member'}), 400
            
        # Create new group
        group = ChatRoom()
        group.name = name
        group.is_group = True
        
        # Add current user
        group.users.append(current_user)
        
        # Add selected members
        for member_id in member_ids:
            member = User.query.get(member_id)
            if member and member != current_user:
                group.users.append(member)
        
        db.session.add(group)
        db.session.commit()
        
        # Emit socket event to notify group members
        user_list = [u for u in group.users if u != current_user]
        for user in user_list:
            socketio.emit(
                'new_notification',
                {
                    'message': f'{current_user.username} added you to group {group.name}',
                    'timestamp': datetime.now().strftime('%H:%M'),
                    'chat_id': group.id,
                    'type': 'group_invite'
                },
                to=f'user_{user.id}'
            )
        
        return jsonify({
            'status': 'success',
            'group_id': group.id
        })
        
    except Exception as e:
        logger.error(f"Error creating group: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create group'}), 500

@app.route('/search_messages')
@login_required
def search_messages():
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'results': []})

        # Get all chats the user is part of
        user_chats = ChatRoom.query.filter(ChatRoom.users.contains(current_user)).all()
        chat_ids = [chat.id for chat in user_chats]

        # Search messages in user's chats
        messages = Message.query.filter(
            Message.chatroom_id.in_(chat_ids),
            Message.content.ilike(f'%{query}%')
        ).order_by(Message.timestamp.desc()).limit(20).all()

        results = []
        for msg in messages:
            results.append({
                'content': msg.content,
                'username': msg.sender.username,
                'timestamp': msg.timestamp.strftime('%H:%M %d/%m/%Y'),
                'chat_id': msg.chatroom_id
            })

        return jsonify({'results': results})

    except Exception as e:
        logger.error(f"Error searching messages: {str(e)}")
        return jsonify({'error': 'Failed to search messages'}), 500

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
        
        if file and file.filename:
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
        message = Message()
        message.content = message_text if message_text else ''
        message.message_type = message_type
        message.file_path = file_path
        message.file_name = file_name
        message.sender_id = current_user.id
        message.chatroom_id = chat_id
        
        db.session.add(message)
        db.session.commit()
        
        # Emit socket event
        socketio.emit(
            'new_message',
            {
                'message': message.content,
                'message_type': message_type,
                'file_path': url_for('static', filename=file_path) if file_path else None,
                'file_name': file_name,
                'username': current_user.username,
                'sender_id': current_user.id,
                'timestamp': message.timestamp.strftime('%H:%M')
            },
            to=str(chat_id)
        )
        
        # Send notifications to other chat members
        user_list = [u for u in chatroom.users if u != current_user]
        for user in user_list:
            notification_message = f'New message from {current_user.username}'
            if chatroom.is_group:
                notification_message += f' in {chatroom.name}'
                
            socketio.emit(
                'new_notification',
                {
                    'message': notification_message,
                    'timestamp': datetime.now().strftime('%H:%M'),
                    'chat_id': chat_id,
                    'sender_id': current_user.id,
                    'type': 'message'
                },
                to=f'user_{user.id}'
            )
        
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
