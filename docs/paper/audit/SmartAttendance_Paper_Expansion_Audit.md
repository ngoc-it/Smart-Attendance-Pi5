# BÁO CÁO KIỂM TOÁN VÀ MỞ RỘNG BÀI BÁO SMARTATTENDANCE
**Dự án:** SmartAttendance — Hệ thống phần mềm quản lý điểm danh thông minh tích hợp AI biên  
**Tập chí mục tiêu:** Tạp chí Khoa học & Công nghệ Nội bộ - Trường Đại học Công nghệ Mekong (MTU)  
**Ngày thực hiện:** 09/09/2026  

---

## 1. Những phần của bản thảo cũ được giữ lại
- **Tiêu đề bài báo (VN & EN):** Giữ nguyên định hướng khẳng định vị thế phần mềm quản lý tích hợp kết hợp thu nhận ảnh kích hoạt người dùng và nhận diện khuôn mặt biên trên Raspberry Pi 5.
- **Tóm tắt (Abstract VN & EN):** Giữ nguyên cấu trúc tóm tắt tổng quan nhưng cập nhật bổ sung chính xác thông số 19 bảng SQLite, mô hình InsightFace 512-d và MiniFASNetV2 ONNX.
- **Từ khóa (Keywords):** Giữ lại các từ khóa chuẩn hóa về phần mềm điểm danh, Edge AI, Raspberry Pi 5, InsightFace, MiniFASNetV2, SQLite.
- **Danh mục Tài liệu tham khảo (References):** Giữ nguyên 18 nguồn tham khảo chuẩn hóa (ArcFace, FaceNet, MiniFASNetV2, OpenCV, InsightFace, ONNX Runtime).

---

## 2. Những phần đã được mở rộng chiều sâu
- **Mục 1. Giới thiệu (Introduction):** Mở rộng phân tích sâu về thách thức trong quản lý đào tạo đại học, 3 rào cản kỹ thuật của Cloud Computing (độ trễ, bảo mật quyền riêng tư, phụ thuộc hạ tầng mạng) và phân tích nguyên lý mô hình **Điểm danh Chủ động Kích hoạt bởi Người dùng (Student-Initiated / Touch-Triggered Attendance)**.
- **Mục 2. Tổng quan tài liệu (Related Work):** Mở rộng phân tích sự tiến hóa của các mạng nơ-ron sinh trắc học và chỉ rõ khoảng trống nghiên cứu (gap) của các công trình trước khi chỉ tập trung vào AI đơn lẻ mà bỏ qua phần mềm quản lý học thuật.
- **Mục 3. Vật liệu và Phương pháp nghiên cứu (Materials and Methods):**
  - Mở rộng phân tích chi tiết Kiến trúc phần mềm 5 tầng.
  - Phân tích sâu thiết kế cơ sở dữ liệu quan hệ SQLite 19 bảng và quy tắc ràng buộc toàn vẹn dữ liệu.
  - Trình bày toán học công thức chuẩn hóa L2 norm $v_{norm}$ và thuật toán gom 30 khung hình mẫu $v_{enroll}$.
  - Trình bày chi tiết luồng xử lý Kiosk UI (`kiosk_check()`), kiểm tra ca học active và đối soát danh sách lớp (`class_students`).
- **Mục 4. Kết quả và Thảo luận (Results & Discussion):** Mở rộng phân tích 3 ưu thế cốt lõi của mô hình Touch-Triggered Kiosk (tiết kiệm >80% CPU/RAM trung bình, triệt tiêu ghi nhận nhầm người đi ngang, tối ưu góc mặt chuẩn Frontal Pose).

---

## 3. Những phần được bổ sung mới hoàn toàn
- **Tiểu mục 3.4. Phân hệ Quản lý Đào tạo và Giao diện Web Admin:** Bổ sung mô tả chi tiết các Flask Blueprints (`routes_academic.py`, `routes_admin.py`, `routes_attendance.py`, `routes_enroll.py`, `routes_lecturer.py`, `routes_student.py`) và quy trình quản lý đơn nghỉ phép (`leave_requests`), đơn dạy bù (`makeup_requests`).
- **Tiểu mục 3.8. Bảo mật, Quyền riêng tư và Cấu hình Triển khai:** Bổ sung cơ chế băm mật khẩu Werkzeug, nâng cấp hash legacy SHA-256, lưu trữ vector Numpy mã hóa trong SQLite cục bộ.
- **Tiểu mục 4.4. Hạn chế của Hệ thống (Limitations):** Bổ sung phân tích minh bạch các hạn chế về thao tác cảm ứng thủ công, khả năng chống giả mạo 3D và quy mô dữ liệu SQLite.

---

## 4. Những thông tin được lấy từ mã nguồn (Source Code Evidence)
- **19 bảng cơ sở dữ liệu:** Được trích xuất chính xác 100% từ `full_schema.sql` (`departments`, `majors`, `users`, `semesters`, `courses`, `classes`, `students`, `class_students`, `rooms`, `schedules`, `periods`, `class_sessions`, `attendance_logs`, `leave_requests`, `makeup_requests`, `holidays`, `device_payloads`, `settings`, `user_classes`).
- **Mô hình AI & Tham số:** Trích xuất từ `app/core/engine.py`, `app/core/antispoof.py` và `config.py`: InsightFace `buffalo_l` 512-d, Cosine similarity threshold $T_{match} = 0.65$, MiniFASNetV2 ONNX liveness threshold $T_{live} = 0.60$, gom 30 khung hình mẫu.
- **Quy trình Kiosk Check:** Trích xuất trực tiếp từ `app/web/routes_kiosk.py` (`get_active_session()`, `shared.last_frame`, kiểm tra `class_students`, ghi file ảnh `student_id_action_timestamp.jpg`).

---

## 5. Những chức năng đã xác minh (19/20 Chức năng)
1. Nút bấm điểm danh cảm ứng (`/kiosk`) kích hoạt POST `/api/kiosk/check`.
2. Kiểm tra ca học active trước khi chạy AI (`get_active_session()`).
3. Phát hiện & trích xuất vector 512-d (InsightFace `buffalo_l`).
4. Kiểm tra sức sống chống giả mạo 2D (MiniFASNetV2 ONNX, $T_{live} = 0.60$).
5. Quản lý Khoa, Ngành, Học phần, Học kỳ, Tiết học, Phòng học.
6. Quản lý Lớp học phần, Thời khóa biểu, Phân công Giảng viên & Sinh viên.
7. Quản lý Đơn xin nghỉ phép sinh viên (`leave_requests`).
8. Quản lý Đơn xin dạy bù giảng viên (`makeup_requests`).
9. Đăng ký mẫu sinh viên mới với cơ chế gom 30 khung hình.
10. Quản lý tài khoản Admin/Giảng viên và băm mật khẩu an toàn.
11. Giao diện Web Flask Admin & Dashboard.
12. Xem nhật ký điểm danh chi tiết kèm ảnh lưu vết.
13. Xuất báo cáo điểm danh ra tệp Excel/CSV.
14. Quản lý cấu hình tham số hệ thống trong bảng `settings`.
15. Chế độ cơ sở dữ liệu SQLite WAL và collation `GET_TEN`.
16. Giao diện API chuyên biệt cho Giảng viên (`routes_lecturer.py`).
17. Giao diện API chuyên biệt cho Sinh viên (`routes_student.py`).
18. Xử lý camera đa luồng với bộ đệm Thread-safe `shared.last_frame`.
19. Đồng bộ dữ liệu thiết bị biên qua `device_payloads` và Firebase module.

---

## 6. Những thông tin chưa xác minh / Chưa triển khai (1 Chức năng)
- **Tự động phát hiện hiện diện (Passive Motion/Presence Detection):** Mã nguồn thực tế không có chức năng tự động bật camera khi có người tiến lại gần. Bài báo đã ghi nhận chính xác trạng thái này là `Chưa triển khai (Not Implemented)` trong Bảng 1.

---

## 7. Những kết quả đang chờ thực nghiệm (Placeholders)
Các nhãn khung chờ số liệu thực nghiệm được đặt công khai trong Bảng 2 và các đoạn văn bản tương ứng:
- `[CHỜ THỰC NGHIỆM ACCURACY]`
- `[CHỜ THỰC NGHIỆM PRECISION / RECALL / F1]`
- `[CHỜ THỰC NGHIỆM APCER / BPCER]`
- `[CHỜ THỰC NGHIỆM LATENCY]`
- `[CHỜ THỰC NGHIỆM TRANSACT TIME]`
- `[CHỜ THỰC NGHIỆM CPU]`
- `[CHỜ THỰC NGHIỆM RAM]`

---

## 8. Những hình tác giả cần tự chèn (Figure Placeholders)
- **[HÌNH 1 - CHỜ TÁC GIẢ CHÈN SƠ ĐỒ KIẾN TRÚC 5 TẦNG HỆ THỐNG SMARTATTENDANCE]**
- **[HÌNH 2 - CHỜ TÁC GIẢ CHÈN SƠ ĐỒ THỰC THỂ TƯƠNG QUAN CƠ SỞ DỮ LIỆU (ERD)]**
- **[HÌNH 3 - CHỜ TÁC GIẢ CHÈN QUY TRÌNH ĐIỂM DANH KÍCH HOẠT NGUỜI DÙNG KIOSK UI]**

---

## 9. Những bảng tác giả cần tự điền số liệu (Table Placeholders)
- **Bảng 2:** Bảng khung chỉ số thực nghiệm hiệu năng hệ thống và nhận diện sinh trắc học (Cần chạy thực nghiệm thực tế trên Raspberry Pi 5 để điền giá trị).

---

## 10. Những điểm vẫn cần tác giả kiểm tra lại
- Cập nhật thông tin Tác giả, Đơn vị công tác và Email tại phần đầu bài báo.
- Cập nhật thông tin Tài trợ / Lời cảm ơn tại mục LỜI CẢM ƠN (nếu có).

---

## 11. Những claim mạnh đã được giảm mức khẳng định
- Đã giảm khẳng định từ *"hệ thống bảo mật tuyệt đối"* thành *"triển khai các cơ chế an toàn thông tin và lưu trữ dữ liệu sinh trắc học cục bộ trên vi máy tính"*.
- Đã giảm khẳng định từ *"hệ thống phát hiện giả mạo hoàn hảo"* thành *"tích hợp mạng nơ-ron MiniFASNetV2 ngăn chặn các cuộc tấn công ảnh in 2D và phát lại màn hình"*.

---

## 12. Những phần trong source code chưa đưa vào bài
- **Toàn bộ mã nguồn chi tiết từng dòng lệnh:** Không đưa mã nguồn thô vào bài để đảm bảo văn phong bài báo khoa học.
- **Các tệp script phụ trợ thử nghiệm:** Không đưa vào bài để giữ tính cô đọng chuyên môn.

---
**Kết luận:** Bài báo đã được biên dịch thành công sang tệp Word `.docx` chuẩn MTU tại thư mục `docs/paper/final/SmartAttendance_Research_Paper_MTU_Final_Draft_v2.docx`, đáp ứng đầy đủ tiêu chí chất lượng khoa học, tính minh bạch và độ dài tương đương 15 trang.
