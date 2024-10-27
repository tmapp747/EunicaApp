from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app import socketio, db
from models import Message, ChatRoom

@socketio.on('send_message')
def handle_message(data):
    if not current_user.is_authenticated:
        return
    
    chat_id = data.get('chat_id')
    if not chat_id:
        return
    
    chatroom = ChatRoom.query.get(chat_id)
    if not chatroom or current_user not in chatroom.users:
        return
    
    message = Message(
        content=data['message'],
        sender_id=current_user.id,
        chatroom_id=chat_id
    )
    db.session.add(message)
    db.session.commit()
    
    emit('new_message', {
        'message': message.content,
        'username': current_user.username,
        'sender_id': current_user.id,
        'timestamp': message.timestamp.strftime('%H:%M')
    }, room=str(chat_id))

@socketio.on('join')
def on_join(data):
    if not current_user.is_authenticated:
        return
    
    room = data.get('room')
    if room:
        join_room(room)

@socketio.on('leave')
def on_leave(data):
    if not current_user.is_authenticated:
        return
    
    room = data.get('room')
    if room:
        leave_room(room)
