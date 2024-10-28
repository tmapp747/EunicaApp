from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from flask import current_app
from app import socketio, db
from models import Message, ChatRoom, User
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        return False
    join_room(f'user_{current_user.id}')
    return True

@socketio.on('error')
def handle_error(error):
    logger.error(f"SocketIO error: {error}")

@socketio.on('send_message')
def handle_message(data):
    try:
        if not current_user.is_authenticated:
            raise ValueError("User not authenticated")
        
        chat_id = data.get('chat_id')
        if not chat_id:
            raise ValueError("No chat ID provided")
        
        chatroom = ChatRoom.query.get(chat_id)
        if not chatroom or current_user not in chatroom.users:
            raise ValueError("Invalid chat room or unauthorized access")
        
        message_content = data.get('message', '').strip()
        message_type = data.get('message_type', 'text')
        file_path = data.get('file_path')
        file_name = data.get('file_name')
        
        message = Message(
            content=message_content,
            message_type=message_type,
            file_path=file_path,
            file_name=file_name,
            sender_id=current_user.id,
            chatroom_id=chat_id
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Prepare message data
        message_data = {
            'message': message.content,
            'message_type': message.message_type,
            'file_path': file_path,
            'file_name': file_name,
            'username': current_user.username,
            'sender_id': current_user.id,
            'timestamp': message.timestamp.strftime('%H:%M')
        }
        
        # Send message to chat room
        emit('new_message', message_data, room=str(chat_id))
        
        # Send notifications to other users in the chat
        notification_data = {
            'message': f'New message from {current_user.username} in {chatroom.name}',
            'timestamp': datetime.now().strftime('%H:%M'),
            'chat_id': chat_id,
            'sender_id': current_user.id
        }
        
        for user in chatroom.users:
            if user.id != current_user.id:
                emit('new_notification', notification_data, room=f'user_{user.id}')
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        emit('message_error', {'error': str(e)}, room=str(chat_id))
        db.session.rollback()
        return False

@socketio.on('join')
def on_join(data):
    try:
        if not current_user.is_authenticated:
            return False
        
        room = data.get('room')
        if not room:
            return False
        
        chatroom = ChatRoom.query.get(room)
        if not chatroom or current_user not in chatroom.users:
            return False
        
        join_room(room)
        return True
        
    except Exception as e:
        logger.error(f"Error joining room: {str(e)}")
        return False

@socketio.on('leave')
def on_leave(data):
    try:
        if not current_user.is_authenticated:
            return False
        
        room = data.get('room')
        if room:
            leave_room(room)
            return True
            
    except Exception as e:
        logger.error(f"Error leaving room: {str(e)}")
        return False
