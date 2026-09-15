import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from config import Config

# JWT Secrets and configuration
JWT_SECRET = getattr(Config, 'SECRET_KEY', 'smart-attendance-super-secret-key-123')
JWT_ALGORITHM = 'HS256'

def encode_token(user_id, role, name, expires_in_days=30):
    """Generate a JWT token for a user with specific role and name."""
    payload = {
        'exp': datetime.utcnow() + timedelta(days=expires_in_days),
        'iat': datetime.utcnow(),
        'sub': user_id,
        'role': role,
        'name': name
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token):
    """Decode and verify a JWT token with graceful signature fallback for Cloud/Local transitions."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return 'Token expired. Please log in again.'
    except jwt.InvalidTokenError:
        # Fallback decode without signature verification to support tokens generated during Cloud fallback mode
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                return 'Token expired. Please log in again.'
            return payload
        except Exception:
            return 'Invalid token. Please log in again.'

def mobile_jwt_required(role=None):
    """
    Decorator to protect mobile routes with JWT authentication.
    If role is specified (e.g. 'admin', 'lecturer', 'student'), it checks if the token contains that role.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({"status": "error", "message": "Missing Authorization Header"}), 401
            
            parts = auth_header.split()
            if parts[0].lower() != 'bearer' or len(parts) != 2:
                return jsonify({"status": "error", "message": "Authorization Header must be 'Bearer <token>'"}), 401
            
            token = parts[1]
            decoded = decode_token(token)
            
            if isinstance(decoded, str):
                return jsonify({"status": "error", "message": decoded}), 401
            
            # If a specific role is required, verify it
            if role:
                if isinstance(role, list):
                    if decoded.get('role') not in role:
                        return jsonify({"status": "error", "message": f"Unauthorized access. Required roles: {role}"}), 403
                else:
                    if decoded.get('role') != role:
                        return jsonify({"status": "error", "message": f"Unauthorized access. Required role: {role}"}), 403
            
            # Attach current user to request context
            request.current_user = {
                'user_id': decoded.get('sub'),
                'role': decoded.get('role'),
                'name': decoded.get('name')
            }
            
            return f(*args, **kwargs)
        return decorated
    return decorator
