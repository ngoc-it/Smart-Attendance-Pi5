# SMARTATTENDANCE — MA TRẬN CHỨC NĂNG PHẦN MỀM (APPLICATION FUNCTIONALITY MATRIX)

Tài liệu này tổng hợp và đối soát toàn bộ các chức năng phần mềm của hệ thống **SmartAttendance** dựa trên bằng chứng mã nguồn thực tế (Source Code Evidence).

---

## MA TRẬN CHỨC NĂNG PHẦN MỀM MÃ NGUỒN (SOURCE CODE FUNCTIONALITY MATRIX)

| ID | Phân hệ (Module) | Chức năng (Function) | Bằng chứng mã nguồn (Source Evidence) | Trạng thái (Status) | Sử dụng trong Bài báo (Paper Usage) |
|---|---|---|---|---|---|
| AF01 | Tương tác Điểm danh (Kiosk UI) | Giao diện cảm ứng điểm danh (`/kiosk`) | `app/web/routes_kiosk.py`, `app/templates/kiosk.html` | CONFIRMED | YES |
| AF02 | Tương tác Điểm danh (Kiosk UI) | Kích hoạt chụp ảnh điểm danh khi chạm nút "Điểm danh" | `app/web/routes_kiosk.py:kiosk_check()` (Endpoint `/api/kiosk/check`) | CONFIRMED | YES |
| AF03 | Tương tác Điểm danh (Kiosk UI) | Phản hồi kết quả điểm danh tức thì (Thành công / Thất bại / Sai lớp) | `app/templates/kiosk.html`, `app/web/routes_kiosk.py` | CONFIRMED | YES |
| AF04 | Quản lý Ca/Tiết học (Session Management) | Kiểm tra ca học đang diễn ra trước khi cho phép điểm danh | `app/database/mixins/schedule.py:get_active_session()`, `routes_kiosk.py` | CONFIRMED | YES |
| AF05 | Thu nhận hình ảnh (Camera Capture) | Thu ảnh từ khung nhớ chung `shared.last_frame` khi có yêu cầu điểm danh | `app/core/shared.py`, `app/core/camera.py`, `routes_kiosk.py` | CONFIRMED | YES |
| AF06 | Xử lý AI Sinh trắc học (Face AI) | Phát hiện & trích xuất vector đặc trưng 512 chiều (InsightFace `buffalo_l`) | `app/core/engine.py:verify_attendance()`, `app/database/models.py` | CONFIRMED | YES |
| AF07 | Xử lý AI Sinh trắc học (Face AI) | Kiểm tra sức sống chống giả mạo 2D (MiniFASNetV2 ONNX, Threshold 0.60) | `app/core/antispoof.py`, `config.py` | CONFIRMED | YES |
| AF08 | Quyết định Điểm danh (Attendance Decision) | Kiểm tra danh sách sinh viên thuộc lớp phần (`class_students`) | `app/database/mixins/class_student.py`, `routes_kiosk.py` | CONFIRMED | YES |
| AF09 | Quy trình Lưu trữ nhật ký (Attendance Logging) | Lưu vết ảnh điểm danh & bản ghi nhật ký (Timestamp, IN/OUT, Class, Room) | `app/database/mixins/attendance.py:log_attendance()`, `routes_kiosk.py` | CONFIRMED | YES |
| AF10 | Quản lý Đăng ký mẫu (Enrollment) | Đăng ký sinh viên mới với cơ chế gom 30 khung hình hợp lệ | `app/web/routes_enroll.py`, `app/templates/enroll.py` | CONFIRMED | YES |
| AF11 | Quản lý Học thuật (Academic Admin) | Quản lý Khoa (`departments`), Ngành (`majors`), Học phần (`courses`) | `app/database/models.py`, `app/database/mixins/academic.py` | CONFIRMED | YES |
| AF12 | Quản lý Đào tạo (Academic Admin) | Quản lý Học kỳ (`semesters`), Phòng học (`rooms`), Tiết học (`periods`) | `app/database/models.py`, `app/web/routes_academic.py` | CONFIRMED | YES |
| AF13 | Quản lý Lớp & Thời khóa biểu (Classes & Schedules) | Quản lý Lớp học phần (`classes`), Thời khóa biểu (`schedules`), Sinh viên - Lớp (`class_students`) | `app/database/mixins/schedule.py`, `app/database/mixins/class_student.py` | CONFIRMED | YES |
| AF14 | Quản lý Người dùng & Phân quyền (User & Auth) | Quản lý tài khoản Admin/Giảng viên (`users`), Xác thực mật khẩu Werkzeug / SHA-256 | `app/database/models.py:verify_login()`, `app/web/routes_auth.py` | CONFIRMED | YES |
| AF15 | Quản lý Nghỉ phép (Leave Requests) | Tạo & duyệt đơn xin nghỉ phép của sinh viên (`leave_requests`) | `app/database/models.py`, `app/api/routes_student.py:submit_leave_request()` | CONFIRMED | YES |
| AF16 | Quản lý Dạy bù (Makeup Requests) | Tạo & duyệt yêu cầu dạy bù (`makeup_requests`) | `app/database/models.py`, `app/database/mixins/lecturer.py` | CONFIRMED | YES |
| AF17 | Cấu hình Hệ thống (System Settings) | Quản lý bảng cấu hình `settings` (ngưỡng so khớp, giới hạn đi muộn) | `app/database/models.py:get_settings()`, `routes_admin.py` | CONFIRMED | YES |
| AF18 | Thống kê & Xuất dữ liệu (Export Reports) | Thống kê danh sách điểm danh & Xuất dữ liệu báo cáo tệp Excel/CSV | `app/web/routes_attendance.py` | CONFIRMED | YES |
| AF19 | Tự động phát hiện hiện diện (Auto Presence Detect) | Tự động phát hiện người tiến lại gần camera và tự khởi động điểm danh | Không có trong mã nguồn | NOT IMPLEMENTED | NO (CẤM NÊU) |
| AF20 | Đồng bộ thời gian thực Đám mây (Cloud Real-time Sync) | Đồng bộ liên tục với Firebase Cloud DB | `config.py` (Đã bị vô hiệu hóa / Inactive) | NOT IMPLEMENTED | NO (CẤM NÊU) |

---

## KẾT LUẬN KIỂM TOÁN VỀ MÔ HÌNH VẬN HÀNH

- **Mô hình Vận hành Chính xác:** Điểm danh **Chủ động do Người dùng Khởi tạo (Student-Initiated / Touch-Triggered Attendance)** kết hợp với **Nhận diện Khuôn mặt Tự động sau khi Chạm**.
- **Không có tính năng tự động phát hiện hiện diện:** Camera KHÔNG tự động kích hoạt điểm danh khi có người đi qua. Sinh viên BẮT BUỘC phải tương tác với màn hình cảm ứng và bấm nút "Điểm danh" để hệ thống bắt đầu quy trình thu ảnh, xử lý AI, kiểm tra danh tính và lưu nhật ký.
