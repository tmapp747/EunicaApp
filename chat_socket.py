from flask_socketio import emit
from flask_login import current_user
from app import socketio, db
from models import Message

@socketio.on('send_message')
def handle_message(data):
    if not current_user.is_authenticated:
        return
    
    message = Message(
        content=data['message'],
        sender_id=current_user.id
    )
    db.session.add(message)
    db.session.commit()
    
    emit('new_message', {
        'message': message.content,
        'username': current_user.username,
        'timestamp': message.timestamp.strftime('%H:%M')
    }, broadcast=True)
