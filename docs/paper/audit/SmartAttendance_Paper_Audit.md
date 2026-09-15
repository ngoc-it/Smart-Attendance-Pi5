# SMARTATTENDANCE — TỔNG HỢP KIỂM TRUYỆN BÀI BÁO KHỜI TẠO BỞI NGUỜI DÙNG (FINAL PAPER AUDIT)

Tài liệu này tổng hợp toàn bộ kết quả đối soát độc lập giữa **Mã nguồn thực tế (Source Code)** và **Nội dung Bài báo Khoa học (Research Paper)** của dự án SmartAttendance.

---

## A. THỰC THI ĐÃ ĐƯỢC XÁC MẠNH (VERIFIED IMPLEMENTATION)
1. **Định vị Hệ thống:** Hệ thống Phần mềm Quản lý Điểm danh Tích hợp (Integrated Attendance Management Software System) gồm 5 tầng kiến trúc: Quản lý Ứng dụng, Tương tác Điểm danh, Nhận diện & Chống giả mạo, Quản lý Dữ liệu, và Thiết bị Biên.
2. **Quy trình Vận hành Khởi tạo bởi Người dùng (Student-Initiated Attendance):**
   - Sinh viên di chuyển tới thiết bị Kiosk.
   - Sinh viên chủ động bấm nút "Điểm danh" trên giao diện cảm ứng Kiosk UI (`/kiosk`).
   - Ứng dụng phát sinh HTTP POST `/api/kiosk/check`.
   - Máy chủ backend tiếp nhận request và thu ảnh từ `shared.last_frame`.
   - Khối AI tự động phát hiện khuôn mặt (InsightFace `buffalo_l`), kiểm tra sức sống 2D (MiniFASNetV2 ONNX) và so khớp Cosine distance ($T_{match}=0.65, T_{live}=0.60$).
   - Hệ thống xác minh danh sách lớp học phần (`class_students`) của ca học đang diễn ra (`get_active_session`).
   - Ghi bản ghi nhật ký vào SQLite `attendance_logs`, lưu ảnh snapshot và phản hồi trạng thái lên màn hình Kiosk.
3. **Các Phân hệ Quản lý Đào tạo:** Quản lý Khoa (`departments`), Ngành (`majors`), Học phần (`courses`), Học kỳ (`semesters`), Tiết học (`periods`), Phòng học (`rooms`), Lớp học phần (`classes`), Thời khóa biểu (`schedules`), Sinh viên (`students`), Tài khoản (`users`), Đơn xin nghỉ phép (`leave_requests`), Đơn xin dạy bù (`makeup_requests`), Cấu hình (`settings`).
4. **Nền tảng phần cứng:** Vi máy tính Raspberry Pi 5 kết hợp Cảm biến Sony IMX708 Camera Module 3.

---

## B. CÁC TUYÊN BỐ CẤM NÊU TRONG BÀI BÁO (CLAIMS THAT MUST NOT BE MADE)
1. **KHÔNG** tuyên bố hệ thống "tự động phát hiện sinh viên khi lại gần" hoặc "camera liên tục quét tự động" (do mã nguồn bắt buộc phải có thao tác bấm nút "Điểm danh" trên Kiosk UI để thu ảnh).
2. **KHÔNG** tuyên bố hệ thống đạt độ chính xác 99% hay FPS 60 khi chưa có nhật ký đo kiểm định lượng thực tế.
3. **KHÔNG** tuyên bố đồng bộ đám mây Firebase thời gian thực (do tính năng này bị vô hiệu hóa trong cấu hình).

---

## C. KẾT QUẢ THỰC NGHIỆM VẮNG MẶT (MISSING EXPERIMENTAL RESULTS)
- Tất cả các vị trí đo kiểm định lượng được thiết lập nhãn khung chờ thực nghiệm (Placeholders) minh bạch:
  * Accuracy / Precision / Recall / F1-score
  * Tỷ lệ lỗi giả mạo APCER / BPCER
  * Thời gian xử lý AI per request (ms)
  * Thời gian giao dịch điểm danh Kiosk UI (ms)
  * Mức tiêu thụ tài nguyên phần cứng (CPU % & RAM MB)

---

## D. HƯỚNG DẪN HÀNH ĐỘNG TIẾP THEO CHO TÁC GIẢ BEFORE SUBMISSION
1. Tiến hành đo kiểm định lượng các chỉ số trên thiết bị Raspberry Pi 5 và điền thay thế các khung chờ `[CHỜ THỰC NGHIỆM ...]` trong tệp `SmartAttendance_Research_Paper_MTU_Final_Draft.docx`.
2. Chèn 3 hình ảnh minh họa (Hình 1 - Kiến trúc 5 tầng, Hình 2 - Luồng điểm danh Kiosk, Hình 3 - Giao diện Web quản lý) vào các vị trí `[HÌNH 1 ...]`, `[HÌNH 2 ...]`, `[HÌNH 3 ...]`.
3. Bổ sung họ tên tác giả và email liên hệ tại khối `[CHỜ THÔNG TIN TÁC GIẢ]`.
4. Xuất tệp Word thành định dạng PDF và nộp cho Ban biên tập Tạp chí Khoa học và Công nghệ MTU.
