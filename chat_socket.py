from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from flask import current_app, url_for
from app import socketio, db
from models import Message, ChatRoom, User
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        logger.warning("Unauthenticated user attempted to connect")
        return False
    logger.info(f"User {current_user.username} connected")
    join_room(f'user_{current_user.id}')
    emit('connection_established', {'user_id': current_user.id, 'username': current_user.username})
    return True

@socketio.on('error')
def handle_error(error):
    logger.error(f"SocketIO error: {error}")
    if current_user.is_authenticated:
        logger.error(f"Error for user {current_user.username}: {error}")

@socketio.on('join')
def on_join(data):
    try:
        if not current_user.is_authenticated:
            logger.warning("Unauthenticated user attempted to join room")
            return False
        
        room = data.get('room')
        if not room:
            logger.error("No room specified in join request")
            return False
        
        # Handle both chat rooms and user-specific rooms
        if isinstance(room, str) and room.startswith('user_'):
            user_id = room.split('_')[1]
            if str(current_user.id) == user_id:
                join_room(room)
                logger.info(f"User {current_user.username} joined notification room {room}")
                emit('room_joined', {'room': room, 'type': 'notification'})
                return True
            else:
                logger.warning(f"User {current_user.username} attempted to join unauthorized notification room {room}")
                return False
        else:
            chatroom = ChatRoom.query.get(room)
            if chatroom and current_user in chatroom.users:
                join_room(str(room))
                logger.info(f"User {current_user.username} joined chat room {room}")
                emit('room_joined', {'room': str(room), 'type': 'chat'})
                return True
            else:
                logger.warning(f"User {current_user.username} attempted to join unauthorized chat room {room}")
                return False
        
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
            logger.info(f"User {current_user.username} left room {room}")
            return True
            
    except Exception as e:
        logger.error(f"Error leaving room: {str(e)}")
        return False

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
        
        # Create and save message
        message = Message()
        message.content = message_content
        message.message_type = message_type
        message.file_path = file_path
        message.file_name = file_name
        message.sender_id = current_user.id
        message.chatroom_id = chat_id
        
        db.session.add(message)
        db.session.commit()
        
        logger.info(f"Message sent by {current_user.username} in chat {chat_id}")
        
        # Prepare message data for chat room
        message_data = {
            'message': message.content,
            'message_type': message.message_type,
            'file_path': url_for('static', filename=file_path) if file_path else None,
            'file_name': file_name,
            'username': current_user.username,
            'sender_id': current_user.id,
            'timestamp': message.timestamp.strftime('%H:%M')
        }
        
        # Emit message to chat room
        emit('new_message', message_data, to=str(chat_id))
        
        # Prepare and send notifications to other users
        notification_data = {
            'message': f'New message from {current_user.username} in {chatroom.name}',
            'timestamp': datetime.now().strftime('%H:%M'),
            'chat_id': chat_id,
            'sender_id': current_user.id,
            'type': 'message'
        }
        
        # Send notifications to all users in the chat except sender
        for user in chatroom.users:
            if user.id != current_user.id:
                user_room = f'user_{user.id}'
                emit('new_notification', notification_data, to=user_room)
                logger.info(f"Sent notification to user {user.username} in room {user_room}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        db.session.rollback()
        emit('message_error', {'error': str(e)}, to=str(data.get('chat_id')) if data.get('chat_id') else None)
        return False
