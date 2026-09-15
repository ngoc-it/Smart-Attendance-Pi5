import re
from config import Config

def validate_password_strength(password):
    """
    Kiểm tra độ mạnh của mật khẩu mới theo các quy chuẩn bảo mật:
    1. Độ dài tối thiểu 8 ký tự.
    2. Phải chứa ít nhất 1 chữ cái viết hoa (A-Z).
    3. Phải chứa ít nhất 1 chữ cái viết thường (a-z).
    4. Phải chứa ít nhất 1 chữ số (0-9).
    5. Phải chứa ít nhất 1 ký tự đặc biệt (!@#$%^&*...).
    6. Không được trùng với mật khẩu mặc định.

    Trả về: (is_valid: bool, error_message: str)
    """
    if not password:
        return False, "Mật khẩu không được để trống!"

    if password == getattr(Config, 'DEFAULT_LECTURER_PASSWORD', 'SmartAttendance@2026'):
        return False, "Mật khẩu mới không được trùng với mật khẩu mặc định của hệ thống!"

    if len(password) < 8:
        return False, "Mật khẩu mới phải có độ dài ít nhất 8 ký tự!"

    if not re.search(r'[A-Z]', password):
        return False, "Mật khẩu mới phải chứa ít nhất 1 chữ cái viết hoa (A-Z)!"

    if not re.search(r'[a-z]', password):
        return False, "Mật khẩu mới phải chứa ít nhất 1 chữ cái viết thường (a-z)!"

    if not re.search(r'[0-9]', password):
        return False, "Mật khẩu mới phải chứa ít nhất 1 chữ số (0-9)!"

    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Mật khẩu mới phải chứa ít nhất 1 ký tự đặc biệt (!@#$%^&*...)!"

    return True, "Mật khẩu hợp lệ!"
