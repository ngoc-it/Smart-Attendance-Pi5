import threading
import socket
from waitress import serve
from app import create_app
from app.core.camera import video_worker, ai_worker

app = create_app()

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == '__main__':
    t_video = threading.Thread(target=video_worker, daemon=True)
    t_video.start()
    
    # t_ai = threading.Thread(target=ai_worker, daemon=True) # TẮT DÒNG NÀY
    # t_ai.start() # TẮT DÒNG NÀY
    
    host_ip = get_ip_address()
    port = 5000
    
    print("\n" + "=" * 55)
    print("SMART ATTENDANCE PRODUCTION SERVER (WAITRESS) IS RUNNING")
    print("=" * 55)
    print(f" Truy cập trên máy này:  http://localhost:{port}")
    print(f"Truy cập trong mạng LAN: http://{host_ip}:{port}")
    print("=" * 55 + "\n")
    
    serve(app, host='0.0.0.0', port=port, threads=16, connection_limit=100)