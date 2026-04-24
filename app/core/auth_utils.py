from functools import wraps
from flask import session, redirect, url_for, request

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def lecturer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'lecturer':
            # Nếu là admin thì đẩy về admin dashboard, nếu chưa login thì đẩy về login
            if session.get('role') == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
