# SMARTATTENDANCE — TÀI LIỆU MÔ TẢ VÀ PHÂN TÍCH TOÀN BỘ PHẦN MỀM TỪ MÃ NGUỒN (REVERSE-ENGINEERED COMPLETE SYSTEM DOCUMENTATION)

**Hệ thống:** SmartAttendance (Điểm danh thông minh dựa trên nhận diện khuôn mặt và quản lý đào tạo)  
**Nền tảng vận hành:** Python 3.11 / Flask / SQLite / ONNX Runtime / OpenCV / Raspberry Pi 5  
**Phương pháp phân tích:** Reverse-Engineering từ Mã nguồn (Static Analysis & Schema Inspection)  
**Ngày phát hành tài liệu:** 09/09/2026  

---

## 1. TỔNG QUAN HỆ THỐNG VÀ BẢN ĐỒ DỰ ÁN (PROJECT MAP & OVERVIEW)

### 1.1. Phần mềm này là gì?
**SmartAttendance** là một hệ thống phần mềm quản lý đào tạo và điểm danh sinh viên sinh trắc học tích hợp đa tầng. Phần mềm cho phép các cơ sở giáo dục đại học quản lý toàn bộ cây dữ liệu học thuật (Khoa, Ngành, Học phần, Học kỳ, Phòng học, Tiết học, Lớp học phần, Thời khóa biểu), thực hiện điểm danh học sinh thông qua Kiosk UI trên màn hình cảm ứng kết hợp nhận diện khuôn mặt và kiểm tra chống giả mạo tại biên (Edge AI), đồng thời xử lý các nghiệp vụ quản lý đơn nghỉ phép, đơn dạy bù, báo cáo thống kê và xuất dữ liệu Excel/CSV.

### 1.2. Đối tượng sử dụng (Actors)
1. **Quản trị viên (Admin):** Quản lý cấu hình hệ thống, quản lý tài khoản người dùng (`users`), quản lý toàn bộ danh mục đào tạo (Khoa, Ngành, Lớp, Học phần, Học kỳ, Phòng học), phân công giảng dạy và cấu hình tham số tham chiếu (`settings`).
2. **Giảng viên (Lecturer / Teacher):** Xem lịch dạy cá nhân, danh sách lớp phụ trách, theo dõi nhật ký điểm danh sinh viên theo thời gian thực, duyệt/từ chối đơn xin nghỉ phép của sinh viên và gửi đơn xin dạy bù (`makeup_requests`).
3. **Sinh viên (Student):** Tương tác với thiết bị Kiosk đặt tại phòng học để bấm nút điểm danh, xem lịch học cá nhân và nộp đơn xin nghỉ phép (`leave_requests`).
4. **Hệ thống Kiosk tự động (Kiosk Terminal UI):** Màn hình cảm ứng chuyên dụng tại phòng học hiển thị ca học active (`get_active_session`) và nút kích hoạt thu nhận ảnh từ camera.

### 1.3. Vấn đề phần mềm giải quyết
- Thay thế hoàn toàn phương pháp điểm danh bằng giấy/ký tên thủ công gây lãng phí 10-15% thời gian tiết học.
- Triệt tiêu nguy cơ gian lận chuyên cần (điểm danh hộ, ký tên hộ, mượn thẻ).
- Vận hành **hoàn toàn Cục bộ (Offline / Edge Computing)** trên vi máy tính Raspberry Pi 5, không phụ thuộc kết nối Internet, không lo rò rỉ dữ liệu sinh trắc học lên Cloud.
- Khắc phục nhược điểm của các hệ thống quét thụ động liên tục bằng mô hình **Điểm danh Chủ động Kích hoạt bởi Người dùng (Student-Initiated / Touch-Triggered)**: sinh viên chủ động ấn nút trên Kiosk UI mới chạy AI, giúp tiết kiệm >80% CPU/RAM và triệt tiêu lỗi nhận diện nhầm người đi ngang.

---

## 2. SƠ ĐỒ KIẾN TRÚC VÀ GIAO TIẾP THỰC TẾ (SYSTEM ARCHITECTURE)

```
                       ┌─────────────────────────────────────────┐
                       │   SINH VIÊN / GIẢNG VIÊN / QUẢN TRỊ     │
                       └────────────────────┬────────────────────┘
                                            │ (HTTP / Browser)
                                            ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │ FRONTEND / USER INTERACTION LAYER                                                   │
 │  ├── Admin Web UI (Flask Jinja2 HTML/CSS/JS): Base, Dashboard, Academic, Admin      │
 │  ├── Kiosk Touch UI (/kiosk): View Active Session & "Điểm danh" Touch Button        │
 │  ├── Student Portal (/student): Timetable, Attendance History, Leave Requests        │
 │  └── Lecturer Portal (/lecturer): Teaching Schedule, Class Log, Makeup Requests     │
 └──────────────────────────────────────────┬──────────────────────────────────────────┘
                                            │ (Flask REST API / Form Submissions)
                                            ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │ BACKEND / BUSINESS LOGIC LAYER (Flask Web Server)                                   │
 │  ├── Web Blueprints: routes_academic, routes_admin, routes_attendance, routes_auth   │
 │  ├── API Blueprints: routes_kiosk, routes_enroll, routes_lecturer, routes_student   │
 │  └── Core Services: auth_utils (Session/Role), importer (Excel/CSV Parser)          │
 └─────────────────────────┬───────────────────────────────────┬───────────────────────┘
                           │                                   │
      (Read/Write Log & Models)                                (Thread Buffer Frame)
                           ▼                                   ▼
 ┌──────────────────────────────────┐        ┌─────────────────────────────────────────┐
 │ DATA MANAGEMENT LAYER            │        │ AI / COMPUTER VISION CORE LAYER         │
 │  ├── SQLite Engine (database.db) │        │  ├── Thread-safe Buffer: shared.last_frame│
 │  ├── 19 Relational Tables        │        │  ├── Camera Worker: GStreamer / OpenCV  │
 │  ├── Custom Collation: GET_TEN   │        │  ├── Face Engine: InsightFace buffalo_l │
 │  └── Journal Mode: WAL           │        │  └── Anti-Spoofing: MiniFASNetV2 ONNX   │
 └──────────────────────────────────┘        └─────────────────────────────────────────┘
                                                               │
                                                    (Hardware Communication)
                                                               ▼
                                             ┌─────────────────────────────────────────┐
                                             │ HARDWARE / EDGE LAYER                   │
                                             │  ├── Vi máy tính Raspberry Pi 5         │
                                             │  └── Sony IMX708 Camera Module 3 (CSI)  │
                                             └─────────────────────────────────────────┘
```

---

## 3. DANH MỤC PHÂN HỆ VÀ CÁC MODULE PHẦN MỀM (MODULE MAP)

### 3.1. Phân hệ Web Administration & Business Routes (`app/web/`)
1. `routes_academic.py`: Quản lý danh mục Khoa (`departments`), Chuyên ngành (`majors`), Học phần (`courses`), Lớp học phần (`classes`), Học kỳ (`semesters`), Tiết học (`periods`), Phòng học (`rooms`), Thời khóa biểu (`schedules`) và nhập liệu tự động từ Excel/CSV.
2. `routes_admin.py`: Quản lý tài khoản Admin/Giảng viên (`users`), cấu hình tham số hệ thống (`settings`), phân công giảng dạy (`user_classes`).
3. `routes_attendance.py`: Quản lý nhật ký điểm danh (`attendance_logs`), xem snapshot ảnh lưu vết, lọc bản ghi theo lớp/ngày, xuất file Excel/CSV.
4. `routes_auth.py`: Đăng nhập, Đăng xuất, Đổi mật khẩu, Quản lý Session.
5. `routes_enroll.py`: Thu thập ảnh mẫu 30 khung hình tạo profile sinh viên mới.
6. `routes_kiosk.py`: Giao diện Kiosk cảm ứng (`/kiosk`) và xử lý điểm danh (`/api/kiosk/check`).

### 3.2. Phân hệ API RESTful (`app/api/`)
1. `routes_student.py`: API dành riêng cho Sinh viên (xem thông tin cá nhân, thời khóa biểu, lịch sử điểm danh, nộp đơn nghỉ phép).
2. `routes_lecturer.py`: API dành riêng cho Giảng viên (xem ca dạy hôm nay, điểm danh thủ công, duyệt đơn nghỉ phép, gửi đơn dạy bù).
3. `routes_auth.py`: API xác thực JWT/Session cho ứng dụng di động/thiết bị ngoài.

### 3.3. Phân hệ Nhân AI & Phần cứng (`app/core/`)
1. `engine.py`: Bộ nhân xử lý nhận diện khuôn mặt InsightFace (`buffalo_l`), trích xuất vector 512 chiều, chuẩn hóa L2 norm, so khớp Cosine distance.
2. `antispoof.py`: Bộ kiểm tra sức sống chống giả mạo 2D MiniFASNetV2 chạy trên ONNX Runtime CPU với ngưỡng $T_{live} = 0.60$.
3. `camera.py`: Luồng thu ảnh liên tục từ camera IMX708 qua chuỗi GStreamer / OpenCV ghi vào bộ nhớ đệm `shared.last_frame`.
4. `shared.py`: Bộ nhớ đệm Thread-safe dùng chung lưu trữ khung hình camera mới nhất.
5. `firebase_sync.py`: Module hỗ trợ đồng bộ dữ liệu phái sinh với Cloud Firebase (mặc định tắt `ENABLE_FIREBASE_SYNC = False`).

---

## 4. CHI TIẾT CƠ SỞ DỮ LIỆU CHUẨN NGHUYÊN THỂ (19 BẢNG SQLITE)

Cơ sở dữ liệu SQLite (`database.db`) bao gồm 19 bảng với cấu trúc schema thực tế trích xuất từ `full_schema.sql`:

```
departments (id, name)
   │
   ├── 1:N ──> majors (id, name, department_id)
   │            │
   │            ├── 1:N ──> courses (id, name, code, credits, lt_credits, th_credits, total_periods, is_mandatory, major_id)
   │            │            │
   │            │            └── 1:N ──> classes (id, name, code, course_id, major_id, semester_id, teacher_id)
   │            │                         │
   │            │                         ├── N:M ──> class_students (class_id, student_id) <── students (id, name, dob, student_class, status, last_seen, password)
   │            │                         ├── 1:N ──> schedules (id, class_id, weekday, start_period_id, num_periods, room_id)
   │            │                         ├── 1:N ──> class_sessions (id, class_id, session_date, start_time, end_time, status, room_id)
   │            │                         ├── 1:N ──> attendance_logs (id, student_id, name, date, time, status, image, room_id, class_id)
   │            │                         ├── 1:N ──> leave_requests (id, student_id, class_id, reason, date, status)
   │            │                         └── 1:N ──> makeup_requests (id, class_id, user_id, requested_date, start_period_id, num_periods, room_id, reason, status)
   │            │
   │            └── 1:N ──> users (id, username, password, role, full_name, email, department_id)
   │                         │
   │                         └── N:M ──> user_classes (user_id, class_id)
   │
semesters (id, name, start_date, end_date, is_current)
periods (id, name, start_time, end_time)
rooms (id, name, capacity, has_camera)
holidays (id, name, holiday_date)
device_payloads (id, room_id, class_id, date, trigger_start, trigger_end, status)
settings (key, value)
```

---

## 5. QUY TRÌNH NGHIỆP VỤ ĐIỂM DANH KIOSK (KIOSK ATTENDANCE WORKFLOW)

```
[SINH VIÊN]                     [KIOSK UI UI/JS]              [BACKEND /ROUTES_KIOSK]            [AI ENGINE & DB]
     │                                │                                │                                │
     │── (1) Đến trước Kiosk ────────>│                                │                                │
     │                                │── (2) GET /current_session ───>│                                │
     │                                │<── (3) Tra ca học active ──────│                                │
     │                                │                                │                                │
     │── (4) Bấm nút "Điểm danh" ────>│                                │                                │
     │                                │── (5) POST /api/kiosk/check ──>│                                │
     │                                │                                │── (6) db.get_active_session() ─>│
     │                                │                                │<── (7) Trả session thông tin ──│
     │                                │                                │                                │
     │                                │                                │── (8) Lấy shared.last_frame ──>│
     │                                │                                │── (9) InsightFace & Antispoof ─>│
     │                                │                                │── (10) Đối soát class_students >│
     │                                │                                │── (11) Ghi attendance_logs ───>│
     │                                │<── (12) Trả kết quả JSON ──────│                                │
     │<── (13) Hiện kết quả + Ảnh ────│                                │                                │
```

### Chi tiết các bước xử lý Backend `kiosk_check()`:
1. **Kiểm tra ca học active:** Gọi `db.get_active_session()`. Nếu không có ca học diễn ra vào thời điểm hiện tại $\rightarrow$ Trả về `403 Forbidden` *"Hiện không có ca học nào đang diễn ra"*.
2. **Kiểm tra bộ đệm camera:** Truy xuất `shared.last_frame`. Nếu `frame is None` $\rightarrow$ Trả về `503 Service Unavailable` *"Camera chưa sẵn sàng"*.
3. **Thực thi AI nhận diện & chống giả mạo:** Gọi `ai_engine.verify_attendance(frame)`.
   - Cắt mặt, resize 80x80 pixels, chạy MiniFASNetV2 ONNX Runtime $\rightarrow$ Lấy điểm liveness $s_{live}$. Ngưỡng $T_{live} = 0.60$. Nếu $s_{live} < 0.60$ $\rightarrow$ Báo lỗi giả mạo khuôn mặt (Spoofing Detected).
   - Trích xuất vector 512 chiều bằng InsightFace `buffalo_l`, chuẩn hóa L2 norm $v_{norm}$. So khớp Cosine distance với danh sách vector trong CSDL. Ngưỡng thành công $T_{match} = 0.65$.
4. **Đối soát danh sách lớp (Class Authorization Check):** Kiểm tra xem `student_id` nhận diện được có nằm trong danh sách lớp học phần (`class_students`) của ca học hay không. Nếu không thuộc lớp $\rightarrow$ Trả về `403 Forbidden` *"Bạn không có trong danh sách lớp này"*.
5. **Ghi nhận bản ghi nhật ký:**
   - Xác định trạng thái điểm danh: Đúng giờ (IN) / Vắng / Đi muộn tùy thuộc vào mốc thời gian cấu hình trong `settings`.
   - Lưu ảnh chụp snapshot vào thư mục `data/log_images/student_id_action_timestamp.jpg`.
   - Thêm bản ghi mới vào bảng `attendance_logs`.
   - Phản hồi dữ liệu JSON gồm họ tên sinh viên, mã sinh viên, trạng thái và đường dẫn ảnh snapshot lên Kiosk UI.

---

## 6. QUY TRÌNH ĐĂNG KÝ VÂN TAY / MẪU KHUÔN MẶT SINH VIÊN (ENROLLMENT PIPELINE)

1. Người quản trị/Cán bộ tạo sinh viên mới trong danh mục `students`.
2. Mở giao diện đăng ký mẫu `/enroll/<student_id>`.
3. Hệ thống bắt đầu bật camera thu thập khung hình liên tục.
4. **Thu thập 30 khung hình hợp lệ:**
   - Hệ thống yêu cầu thu thập đủ $N=30$ khung hình đồng thời thỏa mãn: (1) Phát hiện được 01 khuôn mặt duy nhất; (2) Qua bước chống giả mạo MiniFASNetV2 ($s_{live} \ge 0.60$).
5. **Tính toán Vector Đại diện:**
   - Mặc dù mỗi khung hình tạo ra một vector $v_{norm}^{(k)} \in \mathbb{R}^{512}$, vector đại diện lưu vào CSDL $v_{enroll}$ là trung bình đại số của 30 vector:

$$v_{enroll} = \frac{1}{30} \sum_{k=1}^{30} v_{norm}^{(k)}$$

6. Vector $v_{enroll}$ được serialize dạng chuỗi mảng Numpy mã hóa và lưu vào bảng `students` / thư mục `data/embeddings/`.

---

## 7. ĐẶC TẢ API CHI TIẾT (API SPECIFICATION)

| Endpoint | HTTP Method | Mục đích | Input Parameters | Processing & Logic | Output Response |
| :--- | :---: | :--- | :--- | :--- | :--- |
| `/api/kiosk/current_session` | **GET** | Lấy ca học đang active tại phòng | `room_id` (Query opt) | Query `class_sessions` ghép với `schedules` và `periods` theo thời gian hiện tại | `{status: "success", data: {session_id, class_name, teacher_name, period_info}}` |
| `/api/kiosk/check` | **POST** | Kích hoạt điểm danh từ Kiosk | Form-data / JSON | (1) Active session check $\rightarrow$ (2) Get `shared.last_frame` $\rightarrow$ (3) AI verify & anti-spoof $\rightarrow$ (4) Check `class_students` $\rightarrow$ (5) Save snapshot & log `attendance_logs` | `{status: "success", message: "Điểm danh thành công", student: {id, name, time, image}}` |
| `/enroll/capture/<student_id>` | **POST** | Thu thập frame đăng ký sinh viên | `student_id` (Path) | Đọc `shared.last_frame`, kiểm tra liveness và trích xuất vector embedding 512-d | `{status: "success", count: current_frame_count, progress: percentage}` |
| `/api/student/leave_request` | **POST** | Sinh viên nộp đơn xin nghỉ | `class_id`, `reason`, `date` | Thêm bản ghi mới vào bảng `leave_requests` với trạng thái `PENDING` | `{status: "success", message: "Đã gửi đơn xin nghỉ phép"}` |
| `/api/lecturer/makeup_request` | **POST** | Giảng viên nộp đơn dạy bù | `class_id`, `requested_date`, `period_id`, `room_id`, `reason` | Thêm bản ghi mới vào bảng `makeup_requests` với trạng thái `PENDING` | `{status: "success", message: "Đã gửi đơn xin dạy bù"}` |
| `/api/attendance/export` | **GET** | Xuất báo cáo điểm danh | `class_id`, `start_date`, `end_date`, `format` | Query `attendance_logs`, format bằng Pandas/OpenPyXL | Binary Stream file `.xlsx` hoặc `.csv` |

---

## 8. DANH MỤC QUY TẮC NGHIỆP VỤ (BUSINESS RULES REGISTRY)

1. **Rule 01 - Fail-Fast Attendance:** Không cho phép điểm danh nếu không có ca học active diễn ra vào đúng thời điểm ấn nút trên Kiosk (`db.get_active_session() is None`).
2. **Rule 02 - Class Authorization:** Sinh viên nhận diện đúng mặt nhưng không thuộc danh sách lớp học phần của ca học active (`student_id NOT IN class_students`) sẽ bị từ chối và ghi nhận lỗi `403 Forbidden`.
3. **Rule 03 - Anti-Spoofing Mandatory:** Khung hình có điểm liveness $s_{live} < 0.60$ sẽ lập tức bị hủy bỏ và đánh dấu là tấn công giả mạo (Presentation Attack).
4. **Rule 04 - Biometric Cosine Threshold:** Ngưỡng so khớp vector khuôn mặt thành công bắt buộc đạt $S_{cosine} \ge 0.65$.
5. **Rule 05 - Enrollment Quality Standard:** Bước đăng ký mẫu bắt buộc thu thập đủ 30 khung hình chất lượng cao để tính vector trung bình $v_{enroll}$.
6. **Rule 06 - Password Security:** Mật khẩu người dùng được băm mã hóa bằng Werkzeug pbkdf2:sha256/scrypt. Khi người dùng đăng nhập bằng mật khẩu SHA-256 legacy, hệ thống tự động re-hash sang pbkdf2 để bảo mật.

---

## 9. QUẢN LÝ LỖI VÀ XỬ LÝ NGOẠI LỆ (ERROR HANDLING)

| Mã lỗi / Ngoại lệ | Nguyên nhân phát sinh | Phản hồi hệ thống (System Behavior) | Hiển thị giao diện (User Result) |
| :--- | :--- | :--- | :--- |
| `NO_ACTIVE_SESSION` (403) | Sinh viên bấm điểm danh ngoài giờ học hoặc không có lịch | Trả về JSON HTTP 403 Forbidden | Giao diện Kiosk hiện thông báo đỏ: "Hiện không có ca học nào đang diễn ra" |
| `CAMERA_NOT_READY` (503) | Tiến trình camera chưa ghi được frame nào vào `shared.last_frame` | Trả về JSON HTTP 503 Service Unavailable | Thông báo: "Camera đang khởi động, vui lòng thử lại sau vài giây" |
| `SPOOFING_DETECTED` (400) | Ảnh chụp là ảnh in giấy hoặc màn hình điện thoại ($s_{live} < 0.60$) | Hủy giao dịch điểm danh, không ghi log | Thông báo cảnh báo: "Phát hiện giả mạo khuôn mặt! Vui lòng điểm danh trực tiếp" |
| `NOT_IN_CLASS` (403) | Sinh viên không có tên trong bảng `class_students` của lớp này | Trả về HTTP 403 Forbidden kèm tên sinh viên | Thông báo: "Sinh viên [Tên] không thuộc danh sách lớp học phần này" |
| `UNKNOWN_FACE` (404) | Cosine similarity với toàn bộ CSDL nhỏ hơn ngưỡng 0.65 | Trả về HTTP 404 Not Found | Thông báo: "Không nhận diện được khuôn mặt. Vui lòng đăng ký dữ liệu mẫu" |

---

## 10. PHÂN BIỆT RÕ RÀNG: FACT / INFERENCE / NOT FOUND

| Tính năng / Đặc điểm | Trạng thái kiểm toán mã nguồn | Bằng chứng mã nguồn chi tiết (Source Evidence) |
| :--- | :---: | :--- |
| **Điểm danh kích hoạt chạm nút Kiosk UI** | **IMPLEMENTED / FACT** | Mã nguồn `app/web/routes_kiosk.py` hàm `kiosk_check()`, file HTML `app/templates/kiosk.html`. |
| **Kiểm tra ca học active trước khi chạy AI** | **IMPLEMENTED / FACT** | Hàm `db.get_active_session()` trong `app/core/engine.py`. |
| **Nhận diện khuôn mặt InsightFace 512-d** | **IMPLEMENTED / FACT** | Import `insightface.app.FaceAnalysis(name='buffalo_l')` trong `app/core/engine.py`. |
| **Chống giả mạo MiniFASNetV2 ONNX** | **IMPLEMENTED / FACT** | File `app/core/antispoof.py`, nạp mô hình `MiniFASNetV2.onnx`. |
| **Cơ sở dữ liệu 19 bảng SQLite** | **IMPLEMENTED / FACT** | Khai báo DDL nguyên thể trong file `full_schema.sql`. |
| **Gom 30 khung hình mẫu đăng ký sinh viên** | **IMPLEMENTED / FACT** | Xử lý trong `app/web/routes_enroll.py`. |
| **Quản lý đơn nghỉ phép & dạy bù** | **IMPLEMENTED / FACT** | Bảng `leave_requests` và `makeup_requests` trong schema và các routes tương ứng. |
| **Tự động phát hiện hiện diện (Passive Motion Sensing)** | <span style="color:red">**NOT FOUND**</span> | **Không tìm thấy bất kỳ dòng code nào** triển khai cảm biến khoảng cách/PIR hay tự động bật camera quét thụ động khi có người tiến lại gần. Sinh viên bắt buộc phải bấm nút cảm ứng. |
| **Đồng bộ dữ liệu Cloud Firebase thời gian thực** | **INFERRED (DISABLED)** | Có file `app/core/firebase_sync.py` nhưng mặc định tắt bằng cờ `ENABLE_FIREBASE_SYNC = False` trong `config.py`. |

---

## 11. WHAT THE SYSTEM ACTUALLY DOES (HỆ THỐNG THỰC SỰ LÀM GÌ)

**SmartAttendance** là một ứng dụng web quản lý đào tạo và điểm danh sinh viên sinh trắc học biên chạy trên nền Flask và SQLite. Khi vận hành tại phòng học:
1. Thiết bị Kiosk Raspberry Pi 5 hiển thị giao diện web `/kiosk` trên màn hình cảm ứng.
2. Giao diện định kỳ gọi API lấy ca học hiện tại. Nếu có ca học, Kiosk hiển thị thông tin môn học và giảng viên.
3. Khi sinh viên đến điểm danh, sinh viên **bấm nút *"Điểm danh"* trên màn hình cảm ứng**.
4. Nút bấm kích hoạt gửi HTTP POST `/api/kiosk/check`. Phần mềm kiểm tra điều kiện ca học active, lấy khung hình mới nhất từ camera, thực thi mô hình MiniFASNetV2 để chống giả mạo ảnh 2D và mô hình InsightFace để lấy vector 512 chiều.
5. Phần mềm so khớp vector với CSDL, đối soát mã sinh viên với bảng `class_students`. Nếu hợp lệ, hệ thống lưu bản ghi điểm danh vào `attendance_logs`, lưu ảnh snapshot vào đĩa cứng và phản hồi kết quả lên màn hình Kiosk.
6. Giảng viên và Quản trị viên sử dụng giao diện Web Admin (`/admin`, `/attendance`, `/academic`) để quản lý toàn bộ danh mục đào tạo, xem báo cáo, duyệt đơn xin nghỉ phép và xuất file Excel điểm danh.

---

## 12. WHAT THE SYSTEM DOES NOT DO (HỆ THỐNG KHÔNG LÀM GÌ)

- **KHÔNG tự động quét camera thụ động liên tục khi sinh viên đi ngang qua:** Hệ thống không chạy vòng lặp nhận diện liên tục $24/7$. Sinh viên bắt buộc phải tương tác bấm nút trên màn hình Kiosk thì phần mềm mới bắt đầu thu nhận ảnh và xử lý AI.
- **KHÔNG truyền ảnh sinh trắc học lên Cloud để nhận diện:** Toàn bộ quá trình suy luận AI và lưu trữ dữ liệu diễn ra 100% cục bộ trên vi máy tính Raspberry Pi 5.
- **KHÔNG cho phép sinh viên tự do điểm danh ở bất kỳ ca học nào:** Sinh viên chỉ được công nhận điểm danh nếu có tên trong danh sách lớp học phần (`class_students`) của ca học đang diễn ra.

---

## 13. MA TRẬN TỔNG HỢP CHỨC NĂNG (FUNCTIONALITY MATRIX TABLE)

| Module | Function | Actor | Frontend UI | Backend Route / API | Database Tables | AI / Hardware | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **Kiosk** | Điểm danh cảm ứng | Student | `/kiosk` | `POST /api/kiosk/check` | `attendance_logs`, `class_sessions`, `class_students` | InsightFace, MiniFASNetV2, IMX708 | **FACT** |
| **Kiosk** | Lấy ca học active | System | `/kiosk` | `GET /api/kiosk/current_session` | `class_sessions`, `schedules`, `periods` | None | **FACT** |
| **Academic** | Quản lý Khoa/Ngành | Admin | `/academic/departments` | `GET/POST /academic/departments` | `departments`, `majors` | None | **FACT** |
| **Academic** | Quản lý Học phần/Lớp | Admin | `/academic/courses` | `GET/POST /academic/courses` | `courses`, `classes` | None | **FACT** |
| **Academic** | Quản lý TKB | Admin | `/academic/schedules` | `GET/POST /academic/schedules` | `schedules`, `periods`, `rooms` | None | **FACT** |
| **Enroll** | Đăng ký mẫu 30 ảnh | Admin | `/enroll/<student_id>` | `POST /enroll/capture/<id>` | `students` | InsightFace, MiniFASNetV2, Camera | **FACT** |
| **Attendance** | Xem nhật ký điểm danh | Lecturer/Admin | `/attendance/logs` | `GET /attendance/logs` | `attendance_logs`, `students`, `classes` | None | **FACT** |
| **Attendance** | Xuất báo cáo Excel | Lecturer/Admin | `/attendance/logs` | `GET /api/attendance/export` | `attendance_logs`, `students` | None | **FACT** |
| **Request** | Đơn xin nghỉ phép | Student | `/student/leave` | `POST /api/student/leave_request` | `leave_requests` | None | **FACT** |
| **Request** | Đơn xin dạy bù | Lecturer | `/lecturer/makeup` | `POST /api/lecturer/makeup_request` | `makeup_requests` | None | **FACT** |
| **Admin** | Cấu hình tham số | Admin | `/admin/settings` | `POST /admin/settings` | `settings` | None | **FACT** |
| **Presence** | Tự động phát hiện hiện diện | None | None | None | None | None | <span style="color:red">**NOT FOUND**</span> |

---

## 14. BẢN ĐỒ CẤU TRÚC PHẦN MỀM THỰC TẾ (SYSTEM MODULE MAP)

```
SmartAttendance
│
├── Frontend (Jinja2 Templates & Static Assets)
│   ├── templates/base.html (Khung giao diện chung)
│   ├── templates/kiosk.html (Giao diện điểm danh Kiosk UI)
│   ├── templates/login.html (Giao diện đăng nhập)
│   ├── templates/academic/ (Quản lý Khoa, Ngành, Học phần, Lớp, TKB, Phòng)
│   ├── templates/attendance/ (Nhật ký điểm danh, Snapshot viewer)
│   └── static/ (CSS, JS, Fonts)
│
├── Backend (Flask Application)
│   ├── run.py (Entry point khởi chạy server port 5000 & worker threads)
│   ├── config.py (Cấu hình đường dẫn DB, Models, thresholds)
│   ├── app/__init__.py (Khởi tạo Flask app & đăng ký Blueprints)
│   ├── app/web/ (Web Control Routes)
│   │   ├── routes_academic.py
│   │   ├── routes_admin.py
│   │   ├── routes_attendance.py
│   │   ├── routes_auth.py
│   │   ├── routes_enroll.py
│   │   └── routes_kiosk.py
│   └── app/api/ (RESTful API Routes)
│       ├── routes_lecturer.py
│       ├── routes_student.py
│       └── utils.py
│
├── Data Layer (SQLite Database)
│   ├── full_schema.sql (Khai báo DDL 19 bảng quan hệ)
│   └── data/database/attendance.db (Database thực thi cục bộ)
│
├── AI & Computer Vision Core
│   ├── app/core/engine.py (InsightFace ArcFace 512-d & Cosine similarity)
│   ├── app/core/antispoof.py (MiniFASNetV2 ONNX Runtime Liveness 2D)
│   ├── app/core/camera.py (GStreamer / OpenCV Camera Thread Worker)
│   └── app/core/shared.py (Thread-safe Frame Buffer shared.last_frame)
│
└── Edge Deployment Hardware
    ├── Vi máy tính Raspberry Pi 5 (Broadcom BCM2712 Quad-core ARM)
    └── Sony IMX708 Camera Module 3 (CSI interface)
```

---

## 15. TỆP ĐẦU RA ĐÃ ĐƯỢC TẠO
Tài liệu trên đã được biên dịch hoàn chỉnh và lưu vào file hệ thống tại đường dẫn:
- **`docs/system_documentation/SmartAttendance_Complete_System_Documentation.md`**

*(Tệp tài liệu markdown này chứa đầy đủ thông tin kỹ thuật đảo ngược từ mã nguồn, giúp bất kỳ kỹ sư hoặc AI nào đọc qua cũng có thể thấu hiểu toàn bộ kiến trúc, chức năng và luồng hoạt động thực tế của dự án SmartAttendance).*
