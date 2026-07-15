"""
Task Manager - Day 4 CRUD Project
A complete Flask application demonstrating:
 - User registration & login
 - Session management
 - Password hashing
 - Task CRUD (Create, Read, Update, Delete)
 - Flash messages
 - Dashboard
"""
 
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
 
# ---------------------------------------------------------
# APP CONFIGURATION
# ---------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskmanager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
 
db = SQLAlchemy(app)
 
# ---------------------------------------------------------
# DATABASE MODELS
# ---------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    tasks = db.relationship('Task', backref='owner', cascade='all, delete-orphan')
 
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
 
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
 
 
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending')  # Pending / Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
 
 
# ---------------------------------------------------------
# LOGIN REQUIRED DECORATOR
# ---------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
 
 
# ---------------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------------
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
 
 
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
 
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('register'))
 
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
 
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken. Choose another.', 'danger')
            return redirect(url_for('register'))
 
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
 
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
 
    return render_template('register.html')
 
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
 
        user = User.query.filter_by(username=username).first()
 
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))
 
    return render_template('login.html')
 
 
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))
 
 
# ---------------------------------------------------------
# DASHBOARD / TASK ROUTES (CRUD)
# ---------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    filter_status = request.args.get('status', 'All')
 
    query = Task.query.filter_by(user_id=user_id)
    if filter_status != 'All':
        query = query.filter_by(status=filter_status)
 
    tasks = query.order_by(Task.created_at.desc()).all()
 
    total = Task.query.filter_by(user_id=user_id).count()
    completed = Task.query.filter_by(user_id=user_id, status='Completed').count()
    pending = total - completed
 
    return render_template(
        'dashboard.html',
        tasks=tasks,
        total=total,
        completed=completed,
        pending=pending,
        filter_status=filter_status
    )
 
 
@app.route('/task/add', methods=['POST'])
@login_required
def add_task():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
 
    if not title:
        flash('Task title cannot be empty.', 'danger')
        return redirect(url_for('dashboard'))
 
    new_task = Task(title=title, description=description, user_id=session['user_id'])
    db.session.add(new_task)
    db.session.commit()
 
    flash('Task added successfully.', 'success')
    return redirect(url_for('dashboard'))
 
 
@app.route('/task/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
 
    # Ensure the task belongs to the logged-in user
    if task.user_id != session['user_id']:
        flash('You are not authorized to edit this task.', 'danger')
        return redirect(url_for('dashboard'))
 
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
 
        if not title:
            flash('Task title cannot be empty.', 'danger')
            return redirect(url_for('edit_task', task_id=task_id))
 
        task.title = title
        task.description = description
        db.session.commit()
 
        flash('Task updated successfully.', 'success')
        return redirect(url_for('dashboard'))
 
    return render_template('edit_task.html', task=task)
 
 
@app.route('/task/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
 
    if task.user_id != session['user_id']:
        flash('You are not authorized to delete this task.', 'danger')
        return redirect(url_for('dashboard'))
 
    db.session.delete(task)
    db.session.commit()
 
    flash('Task deleted.', 'info')
    return redirect(url_for('dashboard'))
 
 
@app.route('/task/status/<int:task_id>')
@login_required
def toggle_status(task_id):
    task = Task.query.get_or_404(task_id)
 
    if task.user_id != session['user_id']:
        flash('You are not authorized to update this task.', 'danger')
        return redirect(url_for('dashboard'))
 
    task.status = 'Completed' if task.status == 'Pending' else 'Pending'
    db.session.commit()
 
    flash(f'Task marked as {task.status}.', 'success')
    return redirect(url_for('dashboard'))
 
 
# ---------------------------------------------------------
# APP ENTRY POINT
# ---------------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Creates taskmanager.db and tables if they don't exist
    app.run(debug=True)