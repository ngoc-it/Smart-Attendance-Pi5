/* === ENROLL PAGE LOGIC === */

function startEnroll() {
    const studentId = document.getElementById('student_id').value.trim();
    const name = document.getElementById('name').value.trim();
    const enrollBtn = document.getElementById('enroll-btn');
    const scanLine = document.getElementById('scan-line');
    const progressContainer = document.querySelector('.progress-container');
    const progressBar = document.querySelector('.progress-bar');
    const statusMsg = document.getElementById('status-msg');
    const cameraContainer = document.getElementById('camera-container') || document.querySelector('.camera-preview');

    if (!studentId || !name) {
        alert("Vui lòng điền đủ thông tin sinh viên!");
        return;
    }

    // UI Feedback
    enrollBtn.disabled = true;
    enrollBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang thu thập...';
    scanLine.style.display = "block";
    progressContainer.style.display = "block";
    progressBar.style.width = "10%";
    statusMsg.innerText = "Đang kết nối camera...";
    statusMsg.className = "status-msg msg-info";

    if (cameraContainer) {
        cameraContainer.classList.remove('status-success', 'status-error');
        cameraContainer.classList.add('status-scanning');
    }

    // Cập nhật Step Indicator: Bước 3 - Đang quét
    updateStepIndicator(3);

    const dataContainer = document.getElementById('enroll-meta');
    const classId = dataContainer ? dataContainer.dataset.classId : null;

    // 1. Gửi lệnh bắt đầu thu thập
    fetch('/api/enroll/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            mssv: studentId, 
            name: name,
            dob: document.getElementById('dob').value,
            student_class: document.getElementById('student_class').value,
            course_class_id: classId
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            pollStatus(studentId);
        } else {
            showError(data.message);
        }
    })
    .catch(err => showError("Lỗi kết nối!"));

    function pollStatus(id) {
        let attempts = 0;
        const pollInterval = setInterval(() => {
            attempts++;
            fetch(`/api/enroll/status`)
            .then(res => res.json())
            .then(data => {
                const progress = data.progress || 0;
                // Tính phần trăm trên tổng số 30 ảnh
                const percent = Math.min(Math.round((progress / 30) * 100), 100);
                progressBar.style.width = `${percent}%`;

                // Cập nhật tin nhắn kèm số lượng ảnh sinh động
                if (data.status === 'processing') {
                    statusMsg.innerHTML = `<span class="progress-count">${progress}/30 ảnh</span> - ${data.message}`;
                } else {
                    statusMsg.innerText = data.message;
                }

                if (data.status === 'success') {
                    clearInterval(pollInterval);
                    statusMsg.className = "status-msg msg-success";
                    scanLine.style.display = "none";

                    if (cameraContainer) {
                        cameraContainer.classList.remove('status-scanning');
                        cameraContainer.classList.add('status-success');
                    }

                    // Cập nhật Step Indicator: Bước 4 - Hoàn thành
                    updateStepIndicator(4);
                    progressBar.style.width = "100%";

                    // Hiển thị Overlay Thành công
                    showSuccessOverlay(name, studentId);
                    unlockUI("Hoàn thành");
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    showError(data.message);
                }

                if (attempts > 60) { // Timeout sau 1 phút
                    clearInterval(pollInterval);
                    showError("Hết thời gian chờ (Timeout)!");
                }
            })
            .catch(err => {
                clearInterval(pollInterval);
                showError("Mất kết nối với AI Server!");
            });
        }, 1000);
    }

    function showError(msg) {
        statusMsg.innerText = msg;
        statusMsg.className = "status-msg msg-error";
        progressBar.style.width = "0%";
        if (cameraContainer) {
            cameraContainer.classList.remove('status-scanning');
            cameraContainer.classList.add('status-error');
        }
        setTimeout(() => { if (scanLine) scanLine.style.display = "none"; }, 500);
        updateStepIndicator(2); // Quay lại bước 2 để sẵn sàng nạp lại
        unlockUI("Thử lại");
    }

    function unlockUI(btnText) {
        setTimeout(() => {
            enrollBtn.disabled = false;
            enrollBtn.innerText = btnText || "Bắt đầu thu thập khuôn mặt";
        }, 1500);
    }
}

// Cập nhật sơ đồ các bước Step Indicator
function updateStepIndicator(stepNumber) {
    document.querySelectorAll('.step-item').forEach(item => {
        const step = parseInt(item.dataset.step);
        item.classList.remove('active', 'completed');
        if (step < stepNumber) {
            item.classList.add('completed');
        } else if (step === stepNumber) {
            item.classList.add('active');
        }
    });
}

// Hiển thị cửa sổ popup thành công đếm ngược 3 giây
function showSuccessOverlay(studentName, studentId) {
    let overlay = document.getElementById('success-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'success-overlay';
        overlay.className = 'success-overlay';
        document.body.appendChild(overlay);
    }

    overlay.innerHTML = `
        <div class="success-card">
            <div class="success-icon-wrapper">
                <i class="fas fa-check-circle success-animated-icon"></i>
            </div>
            <h2>Đăng Ký Thành Công!</h2>
            <p class="success-student-info">Sinh viên: <strong>${studentName}</strong> (${studentId})</p>
            <p class="success-detail">Dữ liệu vectơ khuôn mặt đã được lưu trữ & đồng bộ vào RAM thành công.</p>
            
            <div class="countdown-box">
                <div class="countdown-number" id="countdown-num">3</div>
                <div class="countdown-spinner"></div>
            </div>
            
            <p class="countdown-text">Hệ thống đang tự động tải lại danh sách...</p>
            <button class="btn btn-success" style="margin-top: 15px; width: 100%; justify-content: center; font-weight: 600;" onclick="location.reload()">
                <i class="fas fa-sync-alt"></i> Tải lại ngay
            </button>
        </div>
    `;

    overlay.style.display = 'flex';

    let count = 3;
    const countdownInterval = setInterval(() => {
        count--;
        const numEl = document.getElementById('countdown-num');
        if (numEl) numEl.innerText = count;
        if (count <= 0) {
            clearInterval(countdownInterval);
            location.reload();
        }
    }, 1000);
}

function selectStudent(id, name, dob, s_class) {
    document.getElementById('student_id').value = id;
    document.getElementById('name').value = name;
    if (dob && dob !== 'None') document.getElementById('dob').value = dob;
    if (s_class && s_class !== 'None') document.getElementById('student_class').value = s_class;
    
    // Khi chọn nhanh sinh viên từ danh sách, chuyển Step sang Bước 2: Chuẩn bị chụp
    updateStepIndicator(2);

    // Cuộn lên form mượt mà
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function filterByClassEnroll() {
    const classId = document.getElementById('filter_class_enroll').value;
    window.location.href = `/enroll?class_id=${classId}`;
}

function importStudentsEnroll() {
    const fileInput = document.getElementById('import-excel-enroll');
    if (!fileInput.files.length) return;

    const dataContainer = document.getElementById('enroll-meta');
    const classId = dataContainer ? dataContainer.dataset.classId : null;
    
    if (!classId) {
        alert("Vui lòng chọn lớp học ở danh sách phía dưới trước khi import!");
        fileInput.value = '';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('class_id', classId);

    console.log("Đang tải file...");

    fetch('/api/enroll/import', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
            location.reload();
        } else {
            alert("Lỗi import: " + data.message);
        }
    })
    .catch(err => alert("Lỗi kết nối server!"))
    .finally(() => { fileInput.value = ''; });
}

function clearClassStudents() {
    const dataContainer = document.getElementById('enroll-meta');
    const classId = dataContainer ? dataContainer.dataset.classId : null;

    if (!classId) {
        alert("Vui lòng chọn lớp học cần xóa danh sách!");
        return;
    }

    if (!confirm("Bạn có chắc chắn muốn XÓA TOÀN BỘ sinh viên khỏi danh sách lớp này? \n(Lưu ý: Không xóa dữ liệu sinh viên gốc, chỉ xóa khỏi lớp này)")) return;

    fetch('/api/enroll/clear_class', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ class_id: classId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
            location.reload();
        } else {
            alert("Lỗi: " + data.message);
        }
    })
    .catch(err => alert("Lỗi kết nối!"));
}

// Bắt đầu lắng nghe thay đổi thông tin để chuyển sang Bước 2 động
document.addEventListener('DOMContentLoaded', () => {
    const sIdInput = document.getElementById('student_id');
    const nameInput = document.getElementById('name');
    
    if (sIdInput && nameInput) {
        const checkInputs = () => {
            if (sIdInput.value.trim() && nameInput.value.trim()) {
                updateStepIndicator(2);
            } else {
                updateStepIndicator(1);
            }
        };
        sIdInput.addEventListener('input', checkInputs);
        nameInput.addEventListener('input', checkInputs);
    }
});
