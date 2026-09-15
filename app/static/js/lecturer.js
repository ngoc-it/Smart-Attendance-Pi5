/* === LECTURER DASHBOARD LOGIC (OPTION B) === */

let currentStudentId = null;

function filterTable() {
    const input = document.getElementById("searchInput");
    if (!input) return;
    const filter = input.value.toUpperCase();
    const table = document.getElementById("studentTable");
    const tr = table.getElementsByTagName("tr");

    for (let i = 1; i < tr.length; i++) {
        const tdId = tr[i].getElementsByTagName("td")[0];
        const tdName = tr[i].getElementsByTagName("td")[1];
        if (tdId || tdName) {
            const txtValueId = tdId.textContent || tdId.innerText;
            const txtValueName = tdName.textContent || tdName.innerText;
            if (txtValueId.toUpperCase().indexOf(filter) > -1 || txtValueName.toUpperCase().indexOf(filter) > -1) {
                tr[i].style.display = "";
            } else {
                tr[i].style.display = "none";
            }
        }
    }
}

function openActionModal(studentId, studentName) {
    currentStudentId = studentId;
    const classId = document.getElementById('meta-data').dataset.classId;
    
    document.getElementById('modal-student-name').innerText = studentName;
    const sessionSelect = document.getElementById('modal-session');
    sessionSelect.innerHTML = '<option>Đang tải...</option>';
    
    // Fetch sessions within last 7 days
    fetch(`/api/attendance/sessions/${classId}`)
    .then(res => res.json())
    .then(sessions => {
        if (sessions.length === 0) {
            sessionSelect.innerHTML = '<option value="">Không tìm thấy buổi học trong 7 ngày qua</option>';
        } else {
            sessionSelect.innerHTML = sessions.map(s => `
                <option value="${s.session_date}">${s.session_date} (${s.start_time} - ${s.end_time})</option>
            `).join('');
        }
    });

    document.getElementById('action-modal').style.display = 'flex';
}

function closeActionModal() {
    document.getElementById('action-modal').style.display = 'none';
}

function submitManualAction() {
    const date = document.getElementById('modal-session').value;
    const action = document.getElementById('modal-action').value;
    const reason = document.getElementById('modal-reason').value;
    
    if (!date) {
        alert("Vui lòng chọn buổi học!");
        return;
    }

    fetch('/api/attendance/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            id: currentStudentId, 
            action: action, 
            date: date,
            reason: reason 
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            alert("Lỗi: " + data.message);
        }
    });
}

// --- ADD STUDENT MODAL LOGIC ---
function openAddStudentModal() {
    document.getElementById('add-student-modal').style.display = 'flex';
}

function closeAddStudentModal() {
    document.getElementById('add-student-modal').style.display = 'none';
}

function switchTab(tab) {
    // Buttons
    const btns = document.querySelectorAll('.tab-nav-btn');
    btns.forEach(btn => btn.classList.remove('active'));
    if (window.event && window.event.target) {
        const btnTarget = window.event.target.closest('.tab-nav-btn');
        if (btnTarget) btnTarget.classList.add('active');
    }

    // Panes
    const panes = document.querySelectorAll('.tab-pane');
    panes.forEach(pane => pane.classList.remove('active'));
    const targetPane = document.getElementById(`tab-${tab}`);
    if (targetPane) targetPane.classList.add('active');
}

function submitManualEnroll() {
    const mssv = document.getElementById('add-mssv').value;
    const name = document.getElementById('add-name').value;
    const dob = document.getElementById('add-dob').value;
    const s_class = document.getElementById('add-class').value;
    const classId = document.getElementById('meta-data').dataset.classId;

    if (!mssv || !name) {
        alert("Vui lòng nhập MSSV và Họ tên!");
        return;
    }

    fetch('/api/enroll/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            mssv: mssv,
            name: name,
            dob: dob,
            student_class: s_class,
            course_class_id: classId
        })
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

function handleExcelImport() {
    const classId = document.getElementById('meta-data').dataset.classId;
    const fileInput = document.getElementById('excel-file-input');
    if (!fileInput.files.length) return;
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('class_id', classId);

    // Feedback
    const modalContent = document.querySelector('#tab-excel div');
    const originalHTML = modalContent.innerHTML;
    modalContent.innerHTML = '<div style="padding: 20px;"><i class="fas fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary);"></i><p style="margin-top: 10px;">Đang xử lý dữ liệu...</p></div>';

    fetch('/api/enroll/import', { method: 'POST', body: formData })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
            location.reload();
        } else {
            alert("Lỗi import: " + data.message);
            modalContent.innerHTML = originalHTML;
        }
    })
    .catch(err => {
        alert("Lỗi tải lên!");
        modalContent.innerHTML = originalHTML;
    })
    .finally(() => { fileInput.value = ''; });
}

function handleExcelUpload() {
    // Giữ lại hàm cũ để tránh lỗi nếu có nơi nào gọi, nhưng chuyển hướng sang logic mới
    handleExcelImport();
}

// Clock & Initializers
document.addEventListener('DOMContentLoaded', function() {
    // Clock
    const clock = document.getElementById('clock');
    if (clock) {
        setInterval(() => {
            clock.innerText = new Date().toLocaleTimeString('vi-VN');
        }, 1000);
    }

    // Video Feed Auto-refresh
    const videoFeed = document.getElementById('video-feed-img');
    if (videoFeed) {
        setInterval(() => {
            const currentSrc = videoFeed.src.split('?')[0];
            videoFeed.src = currentSrc + "?t=" + new Date().getTime();
        }, 5000);
    }


});
// --- MAKE-UP CLASS LOGIC ---
function openMakeupModal() {
    document.getElementById('makeup-modal').style.display = 'flex';
}

function closeMakeupModal() {
    document.getElementById('makeup-modal').style.display = 'none';
    document.getElementById('slots-container').style.display = 'none';
    document.getElementById('btn-submit-makeup').style.display = 'none';
}

function searchAvailableSlots() {
    const date = document.getElementById('makeup-date').value;
    const num = document.getElementById('makeup-num-periods').value;
    
    if (!date) { alert('Vui lòng chọn ngày!'); return; }
    
    const container = document.getElementById('slots-container');
    const select = document.getElementById('makeup-slot-select');
    const btnSubmit = document.getElementById('btn-submit-makeup');
    
    select.innerHTML = '<option>Đang tìm kiếm...</option>';
    container.style.display = 'block';
    
    fetch(`/api/makeup/available_slots?date=${date}&num_periods=${num}`)
    .then(res => res.json())
    .then(slots => {
        if (slots.length === 0) {
            select.innerHTML = '<option value="">Không tìm thấy slot nào trống</option>';
            btnSubmit.style.display = 'none';
        } else {
            select.innerHTML = slots.map(s => `
                <option value="${s.room_id}|${s.start_period_id}">
                    ${s.period_name} (${s.start_time}) - ${s.room_name}
                </option>
            `).join('');
            btnSubmit.style.display = 'inline-block';
        }
    })
    .catch(err => alert('Lỗi kết nối!'));
}

function submitMakeupRequest() {
    const classSelect = document.getElementById('makeup-class-id');
    const metaData = document.getElementById('meta-data');
    
    let classId = null;
    if (classSelect && classSelect.value) {
        classId = classSelect.value;
    } else if (metaData && metaData.dataset && metaData.dataset.classId) {
        classId = metaData.dataset.classId;
    }

    if (!classId) {
        alert('Vui lòng chọn Lớp học phần!');
        return;
    }

    const date = document.getElementById('makeup-date').value;
    const num = document.getElementById('makeup-num-periods').value;
    const slotData = document.getElementById('makeup-slot-select').value;
    const reason = document.getElementById('makeup-reason').value;
    
    if (!slotData) {
        alert('Vui lòng chọn Slot & Phòng học trống!');
        return;
    }
    const [roomId, startPeriodId] = slotData.split('|');
    
    fetch('/api/makeup/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            class_id: parseInt(classId),
            date: date,
            num_periods: parseInt(num),
            room_id: parseInt(roomId),
            start_period_id: parseInt(startPeriodId),
            reason: reason
        })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        if (data.status === 'success') {
            closeMakeupModal();
            location.reload();
        }
    })
    .catch(err => alert('Lỗi gửi yêu cầu!'));
}

// --- LEAVE REQUEST LOGIC ---
function updateLeaveStatus(requestId, status) {
    if (!confirm(`Bạn chắc chắn muốn ${status === 'Approved' ? 'duyệt' : 'từ chối'} đơn xin nghỉ này?`)) {
        return;
    }
    fetch('/leave/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            request_id: requestId,
            status: status
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            const card = document.getElementById(`leave-req-${requestId}`);
            if (card) {
                card.style.opacity = 0;
                setTimeout(() => {
                    card.remove();
                    const list = document.getElementById('leave-requests-list');
                    const remainingCards = list.querySelectorAll('[id^="leave-req-"]');
                    if (remainingCards.length === 0) {
                        list.innerHTML = '<div style="padding: 20px; text-align: center; color: #888; font-size: 0.9rem;">Không có đơn xin nghỉ nào cần duyệt</div>';
                    }
                }, 200);
            }
        } else {
            alert('Lỗi cập nhật trạng thái đơn phép!');
        }
    })
    .catch(err => {
        console.error(err);
        alert('Lỗi kết nối server!');
    });
}

