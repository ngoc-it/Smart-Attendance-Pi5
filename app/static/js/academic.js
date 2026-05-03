/* === ACADEMIC MANAGEMENT LOGIC === */
const WEEKDAY_MAP = { 2: 'Thứ 2', 3: 'Thứ 3', 4: 'Thứ 4', 5: 'Thứ 5', 6: 'Thứ 6', 7: 'Thứ 7', 8: 'Chủ Nhật' };
const BASE = '/admin/academic';
let modalAction = null, modalId = null;
let currentClassId = null, currentSchedules = [];

function getStaticData(id) {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : [];
}

function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const content = document.getElementById(id);
    if (content) content.style.display = 'block';
    const btn = document.querySelector(`.tab-btn[data-tab="${id}"]`);
    if (btn) btn.classList.add('active');
    localStorage.setItem('activeTabAcademic', id);
}

function showModal(type, id = null, data = {}) {
    modalAction = type;
    modalId = id;
    const overlay = document.getElementById('modal-overlay');
    const body = document.getElementById('modal-body');
    const title = document.getElementById('modal-title');
    const btnSave = document.getElementById('btn-modal-save');
    btnSave.style.display = 'inline-block';
    btnSave.textContent = 'Lưu';

    if (type === 'semester') {
        title.textContent = id ? 'Sửa Học kỳ' : 'Thêm Học kỳ';
        body.innerHTML = `<div class="form-group"><label>Tên Học kỳ</label><input type="text" id="m-name" value="${data.name || ''}" placeholder="VD: HK1 2025-2026" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label>Ngày bắt đầu</label><input type="date" id="m-start" value="${data.start || ''}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label>Ngày kết thúc</label><input type="date" id="m-end" value="${data.end || ''}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>`;
    } else if (type === 'room') {
        title.textContent = id ? 'Sửa Phòng học' : 'Thêm Phòng học';
        body.innerHTML = `<div class="form-group"><label>Tên phòng</label><input type="text" id="m-name" value="${data.name || ''}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label>Sức chứa</label><input type="number" id="m-cap" value="${data.cap || 50}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label><input type="checkbox" id="m-cam" ${data.cam ? 'checked' : ''}> Có Camera nhận diện</label></div>`;
    } else if (type === 'holiday') {
        title.textContent = 'Thêm Ngày nghỉ / Lễ';
        body.innerHTML = `<div class="form-group"><label>Tên ngày lễ</label><input type="text" id="m-name" placeholder="VD: Nghỉ Tết" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
            <div class="form-group"><label>Từ ngày</label><input type="date" id="m-date" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
            <div class="form-group"><label>Đến ngày</label><input type="date" id="m-end-date" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        </div>`;
    } else if (type === 'preview_sessions') {
        title.textContent = 'Xác nhận thay đổi lịch dạy';

        if (currentSchedules.length === 0) {
            btnSave.textContent = 'Xóa toàn bộ lịch';
            body.innerHTML = `<div style="padding:20px; text-align:center; color:red;">
                <h3>⚠️ CẢNH BÁO</h3>
                <p>Bạn đang lưu một thời khóa biểu TRỐNG.</p>
                <p>Toàn bộ các buổi học <strong>CHƯA DIỄN RA</strong> của lớp này sẽ bị <strong>XÓA VĨNH VIỄN</strong>.</p>
                <p>Bạn có chắc chắn muốn thực hiện không?</p>
            </div>`;
        } else {
            btnSave.textContent = 'Xác nhận & Lưu TKB';
            body.innerHTML = `<div style="max-height:400px;overflow-y:auto;border:1px solid #eee;border-radius:8px;">
                <table style="width:100%;border-collapse:collapse;">
                    <thead style="background:#f8fafc;position:sticky;top:0;">
                        <tr><th style="padding:10px;text-align:left;">Buổi</th><th style="padding:10px;text-align:left;">Thứ</th><th style="padding:10px;text-align:left;">Ngày</th><th style="padding:10px;text-align:left;">Giờ</th></tr>
                    </thead>
                    <tbody id="preview-tbody"><tr><td colspan="4" style="text-align:center;padding:20px;">Đang tính toán...</td></tr></tbody>
                </table>
            </div>`;
            fetch(`${BASE}/class/${currentClassId}/sessions/preview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ schedules: currentSchedules })
            }).then(r => r.json()).then(sessions => {
                const tbody = document.getElementById('preview-tbody');
                if (sessions.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:red;">Lỗi: Không thể tính toán buổi học.</td></tr>';
                    btnSave.style.display = 'none';
                    return;
                }
                tbody.innerHTML = sessions.map((s, i) => `<tr><td style="padding:8px;">${i + 1}</td><td style="padding:8px;">${s.weekday}</td><td style="padding:8px;"><strong>${s.date}</strong></td><td style="padding:8px;"><small>${s.time}</small></td></tr>`).join('');
            });
        }
    }
    overlay.style.display = 'flex';
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
        overlay.style.display = 'none';
        document.getElementById('btn-modal-save').style.display = 'block';
    }
}

function saveModal() {
    if (!modalAction) return;
    const name = document.getElementById('m-name')?.value?.trim();

    if (modalAction === 'semester') {
        const start = document.getElementById('m-start').value, end = document.getElementById('m-end').value;
        apiCall(modalId ? `${BASE}/semester/${modalId}` : `${BASE}/semester`, modalId ? 'PUT' : 'POST', { name, start_date: start, end_date: end }, () => location.reload());
    } else if (modalAction === 'room') {
        const cap = parseInt(document.getElementById('m-cap').value) || 50, cam = document.getElementById('m-cam').checked ? 1 : 0;
        apiCall(modalId ? `${BASE}/room/${modalId}` : `${BASE}/room`, modalId ? 'PUT' : 'POST', { name, capacity: cap, has_camera: cam }, () => location.reload());
    } else if (modalAction === 'holiday') {
        const date = document.getElementById('m-date').value, end_date = document.getElementById('m-end-date').value;
        apiCall(`${BASE}/holiday`, 'POST', { name, date, end_date }, () => location.reload());
    } else if (modalAction === 'preview_sessions') {
        fetch(`${BASE}/class/${currentClassId}/schedules`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ schedules: currentSchedules }) })
            .then(r => r.json()).then(d => { alert(d.message); if (d.status === 'success') { closeModal(); document.getElementById('schedule-editor').style.display = 'none'; } });
    }
}

function apiCall(url, method, body, onSuccess) {
    fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        .then(r => r.json()).then(d => { if (d.status === 'success') { closeModal(); if (onSuccess) onSuccess(); } else { alert('Lỗi: ' + d.message); } })
        .catch(err => alert('Lỗi kết nối server!'));
}

document.addEventListener('DOMContentLoaded', function () {
    const savedTab = localStorage.getItem('activeTabAcademic');
    if (savedTab) switchTab(savedTab);

    document.addEventListener('click', function (e) {
        const target = e.target;
        if (target.classList.contains('tab-btn')) switchTab(target.dataset.tab);
        if (target.classList.contains('btn-add')) showModal(target.dataset.type);
        if (target.id === 'btn-modal-cancel' || target.id === 'modal-overlay') closeModal();
        if (target.id === 'btn-modal-save') saveModal();
        const id = target.dataset.id;
        if (target.classList.contains('btn-edit-sem')) showModal('semester', id, { name: target.dataset.name, start: target.dataset.start, end: target.dataset.end });
        if (target.classList.contains('btn-edit-room')) showModal('room', id, { name: target.dataset.name, cap: target.dataset.cap, cam: target.dataset.cam === 'True' });
        if (target.classList.contains('btn-del-room')) { if (confirm('Xóa phòng học này?')) apiCall(`${BASE}/room/${id}`, 'DELETE', {}, () => location.reload()); }
        if (target.classList.contains('btn-set-current-sem')) { if (confirm('Đặt làm Học kỳ hiện tại?')) apiCall(`${BASE}/semester/${id}/set_current`, 'POST', {}, () => location.reload()); }
        if (target.classList.contains('btn-del-sem')) { if (confirm('Xóa học kỳ này?')) apiCall(`${BASE}/semester/${id}`, 'DELETE', {}, () => location.reload()); }
        if (target.id === 'btn-view-schedule') openScheduleEditor();
        if (target.id === 'btn-add-sch-row') addScheduleRow();
        if (target.id === 'btn-save-schedules') saveSchedules();
        if (target.classList.contains('btn-remove-sch')) removeSchedule(target.dataset.index);
        if (target.id === 'btn-recalculate-sessions') recalculateSessions();
        if (target.classList.contains('btn-del-course')) { if (confirm('Xóa học phần này?')) apiCall(`${BASE}/course/${id}`, 'DELETE', {}, () => location.reload()); }
        if (target.classList.contains('btn-del-holiday')) { if (confirm('Xóa ngày nghỉ này?')) apiCall(`${BASE}/holiday/${id}`, 'DELETE', {}, () => location.reload()); }
    });
});

function openScheduleEditor() {
    const id = document.getElementById('class-select').value;
    if (!id) { alert('Chọn lớp trước!'); return; }
    currentClassId = id;
    document.getElementById('schedule-editor').style.display = 'block';
    fetch(`${BASE}/class/${id}/schedules`).then(r => r.json()).then(d => { currentSchedules = d; renderSchedules(); });
}

function renderSchedules() {
    const tbody = document.getElementById('schedule-tbody');
    tbody.innerHTML = '';
    currentSchedules.forEach((s, i) => {
        const wd = WEEKDAY_MAP[s.weekday] || ('T' + s.weekday);
        const pname = s.period_name || ('Tiết ' + s.start_period_id);
        const rname = s.room_name || ('Phòng ' + s.room_id);
        tbody.innerHTML += `<tr><td>${wd}</td><td>${pname}</td><td>${s.num_periods} tiết</td><td>${rname}</td><td><button data-index="${i}" class="btn btn-danger btn-sm btn-remove-sch">Xóa</button></td></tr>`;
    });
}

function addScheduleRow() {
    const wd = document.getElementById('sch-weekday').value, ps = document.getElementById('sch-start-period'), np = document.getElementById('sch-num-periods').value, rs = document.getElementById('sch-room');
    const pid = ps.value, pname = ps.options[ps.selectedIndex]?.text, rid = rs.value, rname = rs.options[rs.selectedIndex]?.text;
    if (!wd || !pid || !np || !rid) { alert('Vui lòng điền đủ thông tin!'); return; }
    currentSchedules.push({ weekday: parseInt(wd), start_period_id: parseInt(pid), period_name: pname.split('(')[0].trim(), num_periods: parseInt(np), room_id: parseInt(rid), room_name: rname });
    renderSchedules();
}

function removeSchedule(i) { currentSchedules.splice(i, 1); renderSchedules(); }

function saveSchedules() {
    if (!currentClassId) return;
    showModal('preview_sessions');
}

function recalculateSessions() {
    if (!currentClassId) return;
    if (!confirm('Hệ thống sẽ xóa tất cả buổi học CHƯA DIỄN RA và sinh lại lịch mới dựa trên thời khóa biểu hiện tại. Tiếp tục?')) return;
    showModal('preview_sessions');
}
