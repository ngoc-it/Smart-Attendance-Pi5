# NỘI DUNG VÀ CẤU TRÚC BÀI BÁO KHOA HỌC (MTU JOURNAL OUTLINE)

**Tên bài báo (Tiếng Việt):**
NGHIÊN CỨU VÀ TRIỂN KHAI HỆ THỐNG PHẦN MỀM QUẢN LÝ ĐIỂM DANH THÔNG MINH TÍCH HỢP THU NHẬN ẢNH KÍCH HOẠT NGUỜI DÙNG VÀ NHẬN DIỆN KHUÔN MẶT TỰ ĐỘNG TRÊN TÍNH TOÁN BIÊN RASPBERRY PI 5

**Title (English):**
RESEARCH AND IMPLEMENTATION OF AN INTEGRATED SMART ATTENDANCE MANAGEMENT SOFTWARE SYSTEM FEATURING USER-INITIATED CAMERA CAPTURE AND AUTOMATED FACE RECOGNITION ON RASPBERRY PI 5 EDGE COMPUTING

---

## MÔ HÌNH ĐỊNH VỊ HỆ THỐNG (SYSTEM POSITIONING)

Hệ thống **SmartAttendance** là một **Phần mềm Hệ thống Quản lý Điểm danh Tích hợp (Integrated Attendance Management Software System)**, bao gồm 5 tầng kiến trúc:
1. **Tầng Quản lý Ứng dụng (Application Management Layer):** Web Flask quản lý Khoa, Ngành, Lớp, Thời khóa biểu, Học kỳ, Tiết học, Tài khoản và Báo cáo.
2. **Tầng Tương tác Điểm danh (Attendance Interaction Layer):** Màn hình cảm ứng Kiosk UI tiếp nhận hành động chạm nút "Điểm danh" từ sinh viên.
3. **Tầng Nhận diện Khuôn mặt (Face Recognition Layer):** Mô hình InsightFace (buffalo_l) và MiniFASNetV2 ONNX anti-spoofing tự động xử lý sau khi được kích hoạt.
4. **Tầng Quản lý Dữ liệu (Data Management Layer):** Cơ sở dữ liệu SQLite quản lý 19 bảng quan hệ.
5. **Tầng Phần cứng / Thiết bị Biên (Hardware / Edge Device Layer):** Vi máy tính Raspberry Pi 5 kết hợp Sony IMX708 Camera Module 3.

**ĐẶC ĐIỂM QUAN TRỌNG VỀ QUY TRÌNH VẬN HÀNH:**
Hệ thống **KHÔNG TỰ ĐỘNG PHÁT HIỆN HIỆN DIỆN** (No Automatic Presence Sensor). Quy trình điểm danh được khởi tạo **CHỦ ĐỘNG BỞI SINH VIÊN (Student-Initiated / Touch-Triggered Attendance)**:
- *Sinh viên đến trước thiết bị Kiosk → Thao tác chạm nút "Điểm danh" → Phần mềm tiếp nhận yêu cầu và kích hoạt Camera thu ảnh → Hệ thống AI tự động phát hiện, chống giả mạo, so khớp sinh trắc học và kiểm tra danh sách lớp → Lưu nhật ký điểm danh vào SQLite và hiển thị kết quả*.

---

## CẤU TRÚC CHI TIẾT BÀI BÁO

### TÓM TẮT & ABSTRACT
- **Tóm tắt (Tiếng Việt):** Trình bày hệ thống phần mềm quản lý điểm danh tích hợp SmartAttendance hoạt động trên vi máy tính Raspberry Pi 5. Nhấn mạnh mô hình điểm danh khởi tạo bởi người dùng qua màn hình cảm ứng Kiosk kết hợp với thị giác máy tính tự động (InsightFace + MiniFASNetV2). Hệ thống giải quyết các bài toán quản lý đào tạo, thời khóa biểu, lịch học và tự động hóa xác thực danh tính offline. (150-200 từ)
- **Từ khóa:** Phần mềm điểm danh, Điểm danh kích hoạt người dùng, Nhận diện khuôn mặt, Edge AI, Raspberry Pi 5, InsightFace, SQLite.
- **Abstract (English):** English abstract. (150-200 words)
- **Keywords:** Attendance Software, Student-Initiated Attendance, Face Recognition, Edge AI, Raspberry Pi 5, InsightFace, SQLite.

### 1. GIỚI THIỆU (INTRODUCTION)
1.1. Bối cảnh & Thách thức trong công tác quản lý điểm danh và đào tạo tại các trường đại học.
1.2. Hạn chế của các giải pháp hiện hữu: Sự phụ thuộc đám mây gây trễ mạng và nguy cơ mất an toàn dữ liệu; Sự nhầm lẫn giữa hệ thống quản lý phần mềm và thuật toán nhận diện đơn lẻ.
1.3. Mô hình đề xuất SmartAttendance: Nền tảng phần mềm quản lý điểm danh toàn diện với cơ chế kích hoạt thu ảnh chủ động (Touch-triggered) kết hợp nhận diện sinh trắc học tự động trên Raspberry Pi 5.
1.4. Đóng góp kỹ thuật và phần mềm của nghiên cứu.

### 2. VẬT LIỆU VÀ PHƯƠNG PHÁP NGHIÊN CỨU (MATERIALS AND METHODS)
2.1. Kiến trúc tổng thể phần mềm hệ thống (5 tầng kiến trúc khép kín).
2.2. Thiết kế phần mềm quản lý điểm danh và đào tạo (Quản lý Khoa, Ngành, Lớp, Học phần, Học kỳ, Tiết học, Đơn nghỉ phép, Đơn dạy bù).
2.3. Thiết kế cơ sở dữ liệu quan hệ SQLite (Cấu trúc 19 bảng và quan hệ giữa Sinh viên, Lớp học phần, Thời khóa biểu, Ca học và Nhật ký điểm danh).
2.4. Quy trình tương tác điểm danh khởi tạo bởi người dùng (User-Initiated Attendance Workflow):
  - Luồng thao tác: *Sinh viên chạm Kiosk → Nút "Điểm danh" → API `/api/kiosk/check` → Thu ảnh Camera → AI Verify → Kiểm tra danh sách lớp → Ghi nhật ký*.
2.5. Cơ chế thu nhận ảnh và xử lý Thị giác máy tính:
  - Thu ảnh từ `shared.last_frame` khi nhận request.
  - Trích xuất đặc trưng InsightFace (`buffalo_l`) chuẩn hóa L2 norm 512-d, so khớp Cosine similarity ($T_{match}=0.65$).
  - Kiểm tra sức sống chống giả mạo 2D với MiniFASNetV2 ONNX ($T_{live}=0.60$).
2.6. Quy trình đăng ký sinh viên (Enrollment 30 khung hình).

### 3. KẾT QUẢ VÀ THẢO LUẬN (RESULTS AND DISCUSSION)
3.1. Kết quả triển khai ứng dụng phần mềm Web Flask & Kiosk UI.
3.2. Bảng tổng hợp các chức năng phần mềm đã xác minh mã nguồn (Bảng chức năng phần mềm).
3.3. Kết quả thực nghiệm nhận diện và hiệu năng phần mềm (Sử dụng nhãn khung chờ `[CHỜ THỰC NGHIỆM]` đối với các chỉ số đo kiểm).
3.4. Thảo luận: So sánh mô hình điểm danh chủ động kích hoạt (Touch-triggered) với mô hình phát hiện liên tục; Phân tích ưu điểm bảo mật và lưu trữ cục bộ.
3.5. Hạn chế của hệ thống (Yêu cầu sinh viên thao tác thủ công nút bấm, chưa hỗ trợ phát hiện hiện diện thụ động từ xa, chưa hỗ trợ chống giả mạo 3D).

### 4. KẾT LUẬN (CONCLUSION)
- Tóm tắt đóng góp về mặt phần mềm quản lý và tự động hóa sinh trắc học.
- Khẳng định tính hiệu quả của mô hình kết hợp kích hoạt người dùng và AI tự động.
- Hướng phát triển tương lai.

### TÀI LIỆU THAM KHẢO (REFERENCES)
- Danh mục 18 tài liệu tham khảo chuẩn IEEE.
