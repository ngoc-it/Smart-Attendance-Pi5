/* === REPORTS PAGE LOGIC === */

function filterReport() {
    const date = document.getElementById('report_date').value;
    const classId = document.getElementById('report_class').value;
    window.location.href = `/reports?date=${date}&class_id=${classId}`;
}

function exportExcel() {
    const date = document.getElementById('report_date').value;
    const classId = document.getElementById('report_class').value;
    
    if (!classId) {
        alert("Vui lòng chọn lớp để xuất báo cáo!");
        return;
    }
    
    window.location.href = `/reports/export?date=${date}&class_id=${classId}`;
}

// Lightbox for snapshots (optional enhancement)
document.addEventListener('DOMContentLoaded', function() {
    const snapshots = document.querySelectorAll('.snapshot-img');
    snapshots.forEach(img => {
        img.onclick = function() {
            // Future: Open larger preview
        };
    });
});
