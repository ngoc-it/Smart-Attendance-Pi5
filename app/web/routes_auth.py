from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role') # 'admin' or 'lecturer'

        user = db.verify_login(username, password, role)
        if user:
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['role'] = user[2]
            
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('attendance.index'))
        else:
            flash('Tài khoản, mật khẩu hoặc quyền đăng nhập không đúng!', 'error')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
