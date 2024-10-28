from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, ChatRoom, Message

@app.route('/')
@login_required
def index():
    return redirect(url_for('chat'))

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
        user = User(
            username=request.form['username'],
            email=request.form['email']
        )
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
        'users'
    ).filter(User.id == current_user.id).all()
    return render_template('chat.html', chatrooms=chatrooms)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

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
