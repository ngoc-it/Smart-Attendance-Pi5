import cv2
import os

os.environ["DISPLAY"] = ":0"

def run_stable_test():
    # Chuỗi GStreamer tối ưu hóa cho IMX708 - Bổ sung bước định dạng I420
    # Đây là định dạng trung gian mà hầu hết ISP và OpenCV đều hiểu
    gst_str = (
        "libcamerasrc ! "
        "video/x-raw, width=640, height=480 ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! "
        "appsink drop=True"
    )

    print("Dang thu nghiem Pipeline: ", gst_str)
    cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("Loi: Pipeline GStreamer khong the khoi tao.")
        # Thu phuong an du phong: Khong resize tai Source
        print("Dang thu phuong an du phong...")
        gst_str_backup = "libcamerasrc ! videoconvert ! video/x-raw, format=BGR ! appsink drop=True"
        cap = cv2.VideoCapture(gst_str_backup, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("Root Cause: Co the camera dang bi treo. Hay thu lenh 'sudo systemctl restart nvgetty' hoac Reboot Pi.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
            
        # Neu anh qua lon (do du phong ko resize), chung ta resize bang tay trong OpenCV
        if frame.shape[1] > 1000:
            frame = cv2.resize(frame, (640, 480))

        cv2.imshow("Smart Attendance - Final Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_stable_test()