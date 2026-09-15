import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_password_reset_email(target_email, otp_code, user_name="Giảng viên"):
    """
    Gửi email OTP lấy lại mật khẩu qua SMTP (Gmail / Custom SMTP).
    Nếu chưa cấu hình SMTP, in OTP ra console để hỗ trợ kiểm thử offline.
    """
    from config import Config
    smtp_server = os.getenv('MAIL_SERVER', getattr(Config, 'MAIL_SERVER', 'smtp.gmail.com'))
    smtp_port = int(os.getenv('MAIL_PORT', getattr(Config, 'MAIL_PORT', 587)))
    smtp_user = os.getenv('MAIL_USERNAME', getattr(Config, 'MAIL_USERNAME', 'diemdanhthongminh2026@gmail.com'))
    smtp_password = os.getenv('MAIL_PASSWORD', getattr(Config, 'MAIL_PASSWORD', 'hqdc ovaq hjmz gbsd')).replace(" ", "")

    print(f"\n=======================================================")
    print(f"PASSWORD RESET OTP FOR [{target_email}]: {otp_code}")
    print(f"=======================================================\n")

    if not smtp_user or not smtp_password:
        print("[MAILER WARN] CHƯA CẤU HÌNH MAIL_USERNAME & MAIL_PASSWORD TRONG ENV.")
        return False, "Chưa cấu hình tài khoản gửi email trên máy chủ."

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[SmartAttendance] Mã OTP khôi phục mật khẩu - {otp_code}"
        msg['From'] = f"SmartAttendance <{smtp_user}>"
        msg['To'] = target_email

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 10px;">
            <h2 style="color: #2563eb; margin-top: 0;">SmartAttendance System</h2>
            <p>Xin chào <strong>{user_name}</strong>,</p>
            <p>Bạn (hoặc ai đó) vừa yêu cầu khôi phục mật khẩu cho tài khoản đăng ký với email này.</p>
            <div style="background: #f1f5f9; padding: 15px; text-align: center; border-radius: 8px; margin: 20px 0;">
                <span style="font-size: 0.85rem; color: #64748b; display: block; margin-bottom: 5px;">MÃ XÁC THỰC OTP CỦA BẠN (HẠN DÙNG 15 PHÚT):</span>
                <strong style="font-size: 2rem; letter-spacing: 5px; color: #1e293b;">{otp_code}</strong>
            </div>
            <p style="font-size: 0.85rem; color: #64748b;">Nếu bạn không yêu cầu thay đổi này, vui lòng bỏ qua email này (vui lòng kiểm tra thêm hộp thư rác/Spam).</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 0.75rem; color: #94a3b8; text-align: center;">Hệ thống Điểm danh Sinh trắc học & Quản lý Đào tạo SmartAttendance</p>
        </div>
        """
        msg.attach(MIMEText(html_body, 'html'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [target_email], msg.as_string())
        server.quit()
        return True, "Mã OTP đã được gửi đến Email của bạn. Vui lòng kiểm tra hộp thư (kể cả Thư rác/Spam)."
    except Exception as e:
        print(f"[MAILER ERROR] Lỗi gửi email qua SMTP: {e}")
        return True, "Mã OTP đã được khởi tạo. Vui lòng kiểm tra hộp thư email của bạn."
