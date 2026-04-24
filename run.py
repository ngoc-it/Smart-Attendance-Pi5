import threading
from app import create_app
from app.core.camera import video_worker, ai_worker

app = create_app()

if __name__ == '__main__':
    t_video = threading.Thread(target=video_worker, daemon=True)
    t_video.start()
    
    # t_ai = threading.Thread(target=ai_worker, daemon=True) # TẮT DÒNG NÀY
    # t_ai.start() # TẮT DÒNG NÀY
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)