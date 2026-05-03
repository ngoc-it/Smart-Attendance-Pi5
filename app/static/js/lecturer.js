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

function handleExcelUpload() {
    const classId = document.getElementById('meta-data').dataset.classId;
    const fileInput = document.getElementById('excel-file');
    if (!fileInput.files.length) return;
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('class_id', classId);

    fetch('/api/enroll/import', { method: 'POST', body: formData })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        if (data.status === 'success') location.reload();
    })
    .catch(err => alert("Lỗi tải lên!"));
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

    // Modal click-outside
    const modal = document.getElementById('action-modal');
    if (modal) {
        modal.onclick = (e) => { if (e.target === modal) closeActionModal(); };
    }
});
