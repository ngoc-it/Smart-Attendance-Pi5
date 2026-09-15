import os
import firebase_admin
from firebase_admin import credentials
from flask import Flask
from config import Config
from app.database.models import AttendanceDB
from app.core.engine import FaceEngine

# Initialize Firebase Admin SDK (Chỉ khởi tạo nếu ENABLE_FIREBASE_SYNC = True)
# if getattr(Config, 'ENABLE_FIREBASE_SYNC', True):
#     firebase_cred_path = Config.FIREBASE_CREDENTIALS_PATH
#     if os.path.exists(firebase_cred_path):
#         try:
#             if not firebase_admin._apps:
#                 cred = credentials.Certificate(firebase_cred_path)
#                 firebase_admin.initialize_app(cred)
#                 print("Firebase Admin SDK initialized successfully.")
#         except Exception as e:
#             print(f"Error initializing Firebase Admin SDK: {e}")
#     else:
#         print(f"Firebase credentials not found at {firebase_cred_path}")
# else:
#     print("Firebase Admin SDK initialization skipped (ENABLE_FIREBASE_SYNC = False).")

# Khởi tạo Singletons bên ngoài hàm để dùng chung
db = AttendanceDB(Config.DB_PATH)
ai_engine = FaceEngine(db)

# Khởi chạy đồng bộ Firebase ngầm (2 chiều) nếu được bật
# if getattr(Config, 'ENABLE_FIREBASE_SYNC', True):
#     from app.core.firebase_sync import start_background_sync
#     start_background_sync(db)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    import logging
    logging.basicConfig(filename='flask_errors.log', level=logging.ERROR)

    # Đăng ký Blueprints
    from app.web.routes_attendance import attendance_bp # Thụt lề 4 khoảng trắng
    from app.web.routes_enroll import enroll_bp # Thụt lề 4 khoảng trắng
    from app.web.routes_kiosk import kiosk_bp
    from app.web.routes_auth import auth_bp
    from app.web.routes_admin import admin_bp
    from app.web.routes_academic import academic_bp
    # from app.api import mobile_bp
    
    app.register_blueprint(attendance_bp) # Thụt lề 4 khoảng trắng
    app.register_blueprint(enroll_bp) # Thụt lề 4 khoảng trắng
    app.register_blueprint(kiosk_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(academic_bp)
    # app.register_blueprint(mobile_bp, url_prefix='/api/mobile')


    @app.route('/api/serve_image/<filename>')
    def serve_image(filename):
        from flask import send_from_directory
        import os
        from config import Config
        return send_from_directory(Config.LOG_IMAGES_DIR, filename)

    return app # Thụt lề 4 khoảng trắng