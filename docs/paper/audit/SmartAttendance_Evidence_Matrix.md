# SMARTATTENDANCE — EVIDENCE MATRIX (MA TRẬN BẰNG CHỨNG MÃ NGUỒN)

| ID | Claim (Tuyên bố) | Evidence (Bằng chứng mã nguồn) | Source File (Tệp nguồn) | Status (Trạng thái) | Paper Usage (Sử dụng trong bài) |
|---|---|---|---|---|---|
| E01 | Điểm danh Chủ động Kích hoạt bởi Người dùng (Student-Initiated Attendance) | Sinh viên chạm nút "Điểm danh" trên Kiosk UI để gửi request POST tới `/api/kiosk/check` kích hoạt lấy frame camera | `app/web/routes_kiosk.py`, `app/templates/kiosk.html` | CONFIRMED | YES (BẮT BUỘC) |
| E02 | Không tự động phát hiện hiện diện (No Auto Presence Sensor) | Không có cảm biến hồng ngoại hay luồng vòng lặp liên tục tự động kích hoạt điểm danh khi người lại gần | Toàn bộ mã nguồn | CONFIRMED (KHÔNG CÓ) | YES (NÊU RÕ HẠN CHẾ) |
| E03 | Vi máy tính Raspberry Pi 5 & Camera Module 3 | Cấu hình camera Picamera2 / libcamera thu luồng video chuẩn CSI | `app/core/camera.py`, `config.py` | CONFIRMED | YES |
| E04 | Mô hình InsightFace (buffalo_l) trên CPU | Khởi tạo InsightFace trích xuất vector 512-d L2 normalized | `app/core/engine.py`, `app/database/models.py` | CONFIRMED | YES |
| E05 | Mô hình Chống giả mạo MiniFASNetV2 ONNX | Thực thi MiniFASNetV2 với ngưỡng xác thực sức sống 0.60 | `app/core/antispoof.py`, `config.py` | CONFIRMED | YES |
| E06 | Ngưỡng so khớp sinh trắc học Cosine = 0.65 | So sánh khoảng cách Cosine với ngưỡng cố định 0.65 trong cấu hình | `app/core/engine.py`, `config.py` | CONFIRMED | YES |
| E07 | Quy trình đăng ký gom 30 khung hình | Gom 30 khung hình hợp lệ liên tiếp tính trung bình đặc trưng | `app/web/routes_enroll.py` | CONFIRMED | YES |
| E08 | Cơ sở dữ liệu SQLite đa bảng | Schema gồm 19 bảng (`students`, `classes`, `users`, `attendance_logs`, `schedules`, `class_sessions`,...) | `app/database/models.py`, `app/database/mixins/` | CONFIRMED | YES |
| E09 | Ứng dụng Quản trị Web Flask | Hệ thống các blueprint Flask (`routes_admin`, `routes_academic`, `routes_attendance`, `routes_kiosk`) | `app/web/` | CONFIRMED | YES |
| E10 | Đơn xin nghỉ & Đơn dạy bù | Tính năng quản lý `leave_requests` và `makeup_requests` | `app/database/models.py`, `app/api/routes_student.py` | CONFIRMED | YES |
| E11 | Thời gian thực FPS / Độ trễ xử lý | Không có nhật ký đo kiểm định lượng FPS/Latency trong mã nguồn | Không có | UNCONFIRMED | NO (DÙNG PLACEHOLDER) |
| E12 | Độ chính xác F1-score / Accuracy | Không có tập dữ liệu kiểm thử thực nghiệm trong mã nguồn | Không có | UNCONFIRMED | NO (DÙNG PLACEHOLDER) |
| E13 | Tự động đồng bộ Firebase Cloud | Tính năng đồng bộ Firebase bị vô hiệu hóa trong cấu hình chính | `config.py` | NOT IMPLEMENTED | NO (HẠN CHẾ) |
