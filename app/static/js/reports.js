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

function exportSummaryExcel() {
    const classId = document.getElementById('report_class').value;
    const start = document.getElementById('summary_start').value;
    const end = document.getElementById('summary_end').value;
    
    if (!classId) {
        alert("Vui lòng chọn lớp để xuất báo cáo tổng kết!");
        return;
    }
    
    let url = `/reports/export_summary?class_id=${classId}`;
    if (start) url += `&start_date=${start}`;
    if (end) url += `&end_date=${end}`;
    
    window.location.href = url;
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
