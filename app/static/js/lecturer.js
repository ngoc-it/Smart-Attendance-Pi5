/* === LECTURER DASHBOARD LOGIC === */

function filterByClass() {
    const classId = document.getElementById('filter_class').value;
    window.location.href = `/?class_id=${classId}`;
}

function filterTable() {
    const input = document.getElementById("searchInput");
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

function updateStatus(studentId, action) {
    fetch('/attendance/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: studentId, action: action })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            alert("Lỗi: " + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Lỗi kết nối server!");
    });
}

function clearClassStudents() {
    const dataContainer = document.getElementById('meta-data');
    const classId = dataContainer.dataset.classId;
    
    if (!classId) return;
    if (confirm("Bạn có chắc chắn muốn xóa TOÀN BỘ sinh viên khỏi lớp này không? Hành động này không thể hoàn tác!")) {
        fetch('/api/enroll/clear_class', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ class_id: classId })
        })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            if (data.status === 'success') location.reload();
        });
    }
}

function handleExcelUpload() {
    const dataContainer = document.getElementById('meta-data');
    const classId = dataContainer.dataset.classId;
    const fileInput = document.getElementById('excel-file');
    
    if (!fileInput.files.length) return;
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('class_id', classId);

    fetch('/api/enroll/import', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        if (data.status === 'success') location.reload();
    })
    .catch(err => alert("Lỗi tải lên!"));
}

// Auto-refresh camera feed timestamp
document.addEventListener('DOMContentLoaded', function() {
    const videoFeed = document.getElementById('video-feed-img');
    if (videoFeed) {
        setInterval(() => {
            const currentSrc = videoFeed.src.split('?')[0];
            videoFeed.src = currentSrc + "?t=" + new Date().getTime();
        }, 5000); // Refresh every 5s to ensure connection
    }
});
