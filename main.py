from app import app, socketio, db
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user, login_required
from models import User, Message

STATIC_USERS = {
    'Bossm': 'Bossm143',
    'Jam': 'Jam143',
    'Buboy': 'Buboy143',
    'Ruel': 'Ruel143',
    'Aira': 'Aira143'
}

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

@app.route('/')
@login_required
def index():
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return render_template('chat.html', messages=messages)

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
