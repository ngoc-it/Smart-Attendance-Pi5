from flask import Blueprint, send_from_directory, jsonify, request
import os
from config import Config
from app.api.utils import mobile_jwt_required

# Create main mobile blueprint
mobile_bp = Blueprint('mobile', __name__)

# Import sub-blueprints
from app.api.routes_auth import mobile_auth_bp
from app.api.routes_student import mobile_student_bp
from app.api.routes_lecturer import mobile_lecturer_bp

# Register sub-blueprints
mobile_bp.register_blueprint(mobile_auth_bp, url_prefix='/auth')
mobile_bp.register_blueprint(mobile_student_bp, url_prefix='/student')
mobile_bp.register_blueprint(mobile_lecturer_bp, url_prefix='/lecturer')

@mobile_bp.route('', methods=['GET'])
@mobile_bp.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "success",
        "message": "Smart Attendance Mobile API is active and running!"
    })

@mobile_bp.route('/image/<filename>', methods=['GET'])
@mobile_jwt_required()
def get_log_image(filename):
    """
    Securely fetch attendance log images.
    Requires a valid JWT token (either lecturer or student).
    """
    # Safeguard against directory traversal attacks
    if '..' in filename or filename.startswith('/'):
        return jsonify({"status": "error", "message": "Invalid filename"}), 400
        
    log_dir = os.path.abspath(os.path.join(os.getcwd(), 'data', 'log_images'))
    file_path = os.path.join(log_dir, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "Image not found"}), 404
        
    return send_from_directory(log_dir, filename)
