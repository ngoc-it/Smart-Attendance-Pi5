from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import db
from app.core.security_utils import validate_password_strength

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role') # 'admin' or 'lecturer'

        user = db.verify_login(username, password, role)
        if user:
            session.permanent = True
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['role'] = user[2]
            session['must_change_password'] = bool(user[3]) if len(user) > 3 else False
            
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('attendance.index'))
        else:
            flash('Tài khoản hoặc mật khẩu không đúng!', 'error')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['POST'])
def change_password():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Vui lòng đăng nhập lại!"}), 401
    
    data = request.get_json() or request.form
    old_pw = data.get('old_password', '').strip()
    new_pw = data.get('new_password', '').strip()
    confirm_pw = data.get('confirm_password', '').strip()
    
    if not old_pw or not new_pw:
        return jsonify({"status": "error", "message": "Vui lòng nhập đầy đủ thông tin!"}), 400
        
    if new_pw != confirm_pw:
        return jsonify({"status": "error", "message": "Mật khẩu xác nhận không khớp!"}), 400
        
    is_valid, err_msg = validate_password_strength(new_pw)
    if not is_valid:
        return jsonify({"status": "error", "message": err_msg}), 400

    success, msg = db.change_user_password(user_id, old_pw, new_pw)
    if success:
        session['must_change_password'] = False
        return jsonify({"status": "success", "message": msg})
    else:
        return jsonify({"status": "error", "message": msg}), 400

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Bước 1: Nhập Username/Email để tạo và gửi mã OTP"""
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        if not identifier:
            flash('Vui lòng nhập Email!', 'error')
            return render_template('forgot_password.html')
            
        from app.core.mailer import send_password_reset_email
        success, msg, otp_code, email, name = db.create_password_reset_token(identifier)
        if success:
            ok, mail_msg = send_password_reset_email(email, otp_code, user_name=name)
            flash(mail_msg, 'success')
            return redirect(url_for('auth.verify_otp', identifier=identifier))
        else:
            flash(msg, 'error')
            
    return render_template('forgot_password.html')

@auth_bp.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """Bước 2: Nhập và kiểm tra mã OTP 6 chữ số"""
    identifier = request.args.get('identifier', '') or request.form.get('identifier', '')
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        otp_code = request.form.get('otp', '').strip()
        
        if not identifier or not otp_code:
            flash('Vui lòng nhập mã OTP!', 'error')
            return render_template('verify_otp.html', identifier=identifier)
            
        success, msg, reset_id, user_id = db.verify_otp_code(identifier, otp_code)
        if success:
            session['otp_verified_reset'] = {
                'identifier': identifier,
                'reset_id': reset_id,
                'user_id': user_id
            }
            return redirect(url_for('auth.reset_password'))
        else:
            flash(msg, 'error')
            return render_template('verify_otp.html', identifier=identifier)
            
    return render_template('verify_otp.html', identifier=identifier)

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """Bước 3: Nhập mật khẩu mới sau khi đã xác thực OTP thành công"""
    reset_session = session.get('otp_verified_reset')
    if not reset_session:
        flash('Phiên làm việc đã hết hạn!', 'error')
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        new_pw = request.form.get('new_password', '').strip()
        confirm_pw = request.form.get('confirm_password', '').strip()
        
        if not new_pw or not confirm_pw:
            flash('Vui lòng nhập mật khẩu mới!', 'error')
            return render_template('reset_password.html')
            
        if new_pw != confirm_pw:
            flash('Mật khẩu xác nhận không khớp!', 'error')
            return render_template('reset_password.html')
            
        if len(new_pw) < 6:
            flash('Mật khẩu tối thiểu 6 ký tự!', 'error')
            return render_template('reset_password.html')
            
        is_valid, err_msg = validate_password_strength(new_pw)
        if not is_valid:
            flash(err_msg, 'error')
            return render_template('reset_password.html')
            
        reset_id = reset_session['reset_id']
        user_id = reset_session['user_id']
        
        success, msg = db.reset_password_after_otp(reset_id, user_id, new_pw)
        if success:
            session.pop('otp_verified_reset', None)
            flash(msg, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(msg, 'error')
            
    return render_template('reset_password.html')

