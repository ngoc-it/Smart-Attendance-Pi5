/* === ENROLL PAGE LOGIC === */

function startEnroll() {
    const studentId = document.getElementById('student_id').value;
    const name = document.getElementById('name').value;
    const enrollBtn = document.getElementById('enroll-btn');
    const scanLine = document.getElementById('scan-line');
    const progressContainer = document.querySelector('.progress-container');
    const progressBar = document.querySelector('.progress-bar');
    const statusMsg = document.getElementById('status-msg');

    if (!studentId || !name) {
        alert("Vui lòng điền đủ thông tin sinh viên!");
        return;
    }

    // UI Feedback
    enrollBtn.disabled = true;
    enrollBtn.innerText = "Đang thu thập...";
    scanLine.style.display = "block";
    progressContainer.style.display = "block";
    progressBar.style.width = "10%";
    statusMsg.innerText = "Đang kết nối camera...";
    statusMsg.className = "status-msg msg-info";

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
                progressBar.style.width = `${progress}%`;
                statusMsg.innerText = data.message;

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    statusMsg.className = "status-msg msg-success";
                    scanLine.style.display = "none";
                    unlockUI("Hoàn thành! ✅");
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    showError(data.message);
                }

                if (attempts > 60) { // Timeout after 1 minute
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
        setTimeout(() => { scanLine.style.display = "none"; }, 500);
        unlockUI("Thử lại");
    }

    function unlockUI(btnText) {
        setTimeout(() => {
            enrollBtn.disabled = false;
            enrollBtn.innerText = btnText || "Bắt đầu thu thập khuôn mặt";
        }, 1500);
    }
}

function selectStudent(id, name, dob, s_class) {
    document.getElementById('student_id').value = id;
    document.getElementById('name').value = name;
    if (dob && dob !== 'None') document.getElementById('dob').value = dob;
    if (s_class && s_class !== 'None') document.getElementById('student_class').value = s_class;
    
    // Cuộn lên form
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function filterByClassEnroll() {
    const classId = document.getElementById('filter_class_enroll').value;
    window.location.href = `/enroll?class_id=${classId}`;
}

