# SMARTATTENDANCE — BÁO CÁO PHẢN BIỆN KHOA HỌC (REVIEWER REPORT)

**Tên bài báo:** NGHIÊN CỨU VÀ TRIỂN KHAI HỆ THỐNG PHẦN MỀM QUẢN LÝ ĐIỂM DANH THÔNG MINH TÍCH HỢP THU NHẬN ẢNH KÍCH HOẠT NGƯỜI DÙNG VÀ NHẬN DIỆN KHUÔN MẶT TỰ ĐỘNG TRÊN TÍNH TOÁN BIÊN RASPBERRY PI 5  
**Đơn vị gửi:** Tạp chí Khoa học và Công nghệ Trường Đại học Công nghệ Mekong (MTU)  
**Vai trò:** Hội đồng Phản biện Tạp chí Khoa học MTU  

---

## TỔNG QUAN ĐÁNH GIÁ (OVERALL ASSESSMENT)

Bài báo đã làm rõ định vị dự án **SmartAttendance** như một **Hệ thống Phần mềm Quản lý Điểm danh Tích hợp (Integrated Attendance Management Software System)** complete thay vì một thuật toán nhận diện khuôn mặt đơn lẻ. 

Đặc biệt, bài báo đã trình bày chính xác mô hình vận hành thực tế: **Điểm danh Chủ động Kích hoạt bởi Người dùng (Student-Initiated / Touch-Triggered Attendance)**. Hệ thống KHÔNG tự động phát hiện sự hiện diện của sinh viên (No Auto Presence Sensor) mà quy trình thu ảnh camera chỉ bắt đầu sau khi sinh viên ấn nút "Điểm danh" trên giao diện cảm ứng Kiosk UI (`/kiosk`). Khâu nhận diện khuôn mặt InsightFace và chống giả mạo MiniFASNetV2 tự động xử lý xác thực danh tính ngay sau khi được khởi tạo.

---

## CÁC PHÁT HIỆN VÀ YÊU CẦU CHỈNH SỬA

### 1. PHÁT HIỆN NGHIÊM TRỌNG (CRITICAL FINDINGS)
- **CRIT-01: Tuyệt đối không được mô tả sai lệch cơ chế vận hành.**
  - *Đã xác minh:* Bài báo đã chỉnh sửa và mô tả chuẩn xác luồng tương tác chạm Kiosk UI. Không sử dụng các cụm từ sai lệch như "tự động phát hiện người", "camera tự động nhận diện sinh viên khi lại gần".
- **CRIT-02: Điền đầy đủ các khung chờ thực nghiệm.**
  - *Yêu cầu:* Tác giả cần chạy kiểm thử thực nghiệm độ chính xác (Accuracy, F1), thời gian giao dịch điểm danh (Transact Time) và tài nguyên CPU/RAM trên vi máy tính Raspberry Pi 5 để điền vào Bảng 2 trước khi xuất bản.

### 2. PHÁT HIỆN LỚN (MAJOR FINDINGS)
- **MAJ-01: Bổ sung hình minh họa giao diện Kiosk UI và sơ đồ 5 tầng kiến trúc.**
  - *Yêu cầu:* Chèn sơ đồ kiến trúc 5 tầng vào vị trí `[HÌNH 1 ...]` và sơ đồ luồng điểm danh chạm nút vào vị trí `[HÌNH 2 ...]`.

### 3. PHÁT HIỆN NHỎ (MINOR FINDINGS)
- **MIN-01: Định dạng trích dẫn IEEE.**
  - *Xác nhận:* 18 tài liệu tham khảo trong danh mục đã tuân thủ chuẩn IEEE và khớp với các chỉ số trích dẫn [1]-[18] trong bài.

---

## KẾT LUẬN CỦA PHẢN BIỆN (REVIEWER DECISION)

**Quyết định:** **Chấp nhận nộp bản hoàn chỉnh (Accept upon inserting real experimental metrics into placeholders)**.  
Bài báo có lập luận khoa học chặt chẽ, mô tả chính xác cơ chế phần mềm thực tế trong mã nguồn và trung thực về mặt dữ liệu.
