from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, ChatRoom, Message

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user = User(username=request.form['username'])
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/chat')
@login_required
def chat():
    chatrooms = ChatRoom.query.join(
        ChatRoom.users
    ).filter(User.id == current_user.id).all()
    
    # Get all users for creating new chats
    users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('chat.html', 
                         chatrooms=chatrooms,
                         users=users,
                         active_chat=None,
                         messages=[])

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/chat/<int:chatroom_id>')
@login_required
def view_chat(chatroom_id):
    chatroom = ChatRoom.query.get_or_404(chatroom_id)
    if current_user not in chatroom.users:
        flash('Access denied')
        return redirect(url_for('chat'))
        
    chatrooms = ChatRoom.query.join(
        'users'
    ).filter(User.id == current_user.id).all()
    
    users = User.query.filter(User.id != current_user.id).all()
    messages = Message.query.filter_by(chatroom_id=chatroom_id).order_by(Message.timestamp).all()
    
    return render_template('chat.html',
                         chatrooms=chatrooms,
                         users=users,
                         active_chat=chatroom,
                         messages=messages)

@app.route('/chatroom/create', methods=['POST'])
@login_required
def create_chatroom():
    try:
        chatroom = ChatRoom(
            name=request.form['name'],
            is_group=True
        )
        chatroom.users.append(current_user)
        db.session.add(chatroom)
        db.session.commit()
        return redirect(url_for('chat'))
    except Exception as e:
        db.session.rollback()
        flash('Error creating chat room', 'error')
        return redirect(url_for('chat'))
