from flask import Flask
from config import Config
from app.database.models import AttendanceDB
from app.core.engine import FaceEngine

# Khởi tạo Singletons bên ngoài hàm để dùng chung
db = AttendanceDB(Config.DB_PATH)
ai_engine = FaceEngine(db)

def create_app():
    app = Flask(__name__)  # Thụt lề 4 khoảng trắng
    app.config.from_object(Config) # Thụt lề 4 khoảng trắng

    # Đăng ký Blueprints
    from app.web.routes_attendance import attendance_bp # Thụt lề 4 khoảng trắng
    from app.web.routes_enroll import enroll_bp # Thụt lề 4 khoảng trắng
    from app.web.routes_kiosk import kiosk_bp
    from app.web.routes_auth import auth_bp
    from app.web.routes_admin import admin_bp
    from app.web.routes_academic import academic_bp
    
    app.register_blueprint(attendance_bp) # Thụt lề 4 khoảng trắng
    app.register_blueprint(enroll_bp) # Thụt lề 4 khoảng trắng
    app.register_blueprint(kiosk_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(academic_bp)

    @app.route('/api/serve_image/<filename>')
    def serve_image(filename):
        from flask import send_from_directory
        import os
        from config import Config
        return send_from_directory(Config.LOG_IMAGES_DIR, filename)

    return app # Thụt lề 4 khoảng trắng