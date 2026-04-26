/* === ACADEMIC MANAGEMENT LOGIC === */
const WEEKDAY_MAP = { 2: 'Thứ 2', 3: 'Thứ 3', 4: 'Thứ 4', 5: 'Thứ 5', 6: 'Thứ 6', 7: 'Thứ 7', 8: 'Chủ Nhật' };
const BASE = '/admin/academic';
let modalAction = null, modalId = null;
let currentClassId = null, currentSchedules = [];

// Fetch data from hidden HTML elements
function getStaticData(id) {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : [];
}

// --- CORE FUNCTIONS ---
function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    
    const content = document.getElementById(id);
    if (content) content.style.display = 'block';
    
    const btn = document.querySelector(`.tab-btn[data-tab="${id}"]`);
    if (btn) btn.classList.add('active');

    // Lưu tab vào localStorage
    localStorage.setItem('activeTabAcademic', id);
}

function showModal(type, id = null, data = {}) {
    modalAction = type;
    modalId = id;
    const overlay = document.getElementById('modal-overlay');
    const body = document.getElementById('modal-body');
    const title = document.getElementById('modal-title');

    if (type === 'semester') {
        title.textContent = id ? 'Sửa Học kỳ' : 'Thêm Học kỳ';
        body.innerHTML = `<div class="form-group"><label>Tên Học kỳ</label><input type="text" id="m-name" value="${data.name || ''}" placeholder="VD: HK1 2025-2026" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label>Ngày bắt đầu</label><input type="date" id="m-start" value="${data.start || ''}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label>Ngày kết thúc</label><input type="date" id="m-end" value="${data.end || ''}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        ${id ? `<p style="color:red;font-size:0.8rem;margin-top:10px;">⚠️ Lưu ý: Khi đổi ngày, toàn bộ buổi học của các lớp trong hệ thống sẽ được tính toán lại.</p>` : ''}`;
    } else if (type === 'room') {
        title.textContent = id ? 'Sửa Phòng học' : 'Thêm Phòng học';
        body.innerHTML = `<div class="form-group"><label>Tên phòng</label><input type="text" id="m-name" value="${data.name || ''}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label>Sức chứa</label><input type="number" id="m-cap" value="${data.cap || 50}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label><input type="checkbox" id="m-cam" ${data.cam ? 'checked' : ''}> Có Camera nhận diện</label></div>`;
    }
    overlay.style.display = 'flex';
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

function apiCall(url, method, body, onSuccess) {
    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
    .then(r => r.json())
    .then(d => {
        if (d.status === 'success') {
            closeModal();
            if (onSuccess) onSuccess();
        } else {
            alert('Lỗi: ' + d.message);
        }
    })
    .catch(err => alert('Lỗi kết nối server!'));
}

function saveModal() {
    const name = document.getElementById('m-name')?.value?.trim();
    if (!modalAction) return;

    if (modalAction === 'semester') {
        const start = document.getElementById('m-start').value;
        const end = document.getElementById('m-end').value;
        apiCall(modalId ? `${BASE}/semester/${modalId}` : `${BASE}/semester`, modalId ? 'PUT' : 'POST', { name, start_date: start, end_date: end }, () => location.reload());
    } else if (modalAction === 'room') {
        const cap = parseInt(document.getElementById('m-cap').value) || 50;
        const cam = document.getElementById('m-cam').checked ? 1 : 0;
        apiCall(modalId ? `${BASE}/room/${modalId}` : `${BASE}/room`, modalId ? 'PUT' : 'POST', { name, capacity: cap, has_camera: cam }, () => location.reload());
    }
}

// --- EVENT LISTENERS ---
document.addEventListener('DOMContentLoaded', function() {
    // Khôi phục tab từ localStorage
    const savedTab = localStorage.getItem('activeTabAcademic');
    if (savedTab) switchTab(savedTab);

    document.addEventListener('click', function(e) {
        const target = e.target;
        if (target.classList.contains('tab-btn')) switchTab(target.dataset.tab);
        if (target.classList.contains('btn-add')) showModal(target.dataset.type);
        if (target.id === 'btn-modal-cancel' || target.id === 'modal-overlay') closeModal();
        if (target.id === 'btn-modal-save') saveModal();

        const id = target.dataset.id;
        if (target.classList.contains('btn-edit-sem')) {
            showModal('semester', id, { name: target.dataset.name, start: target.dataset.start, end: target.dataset.end });
        }
        if (target.classList.contains('btn-edit-room')) {
            showModal('room', id, { name: target.dataset.name, cap: target.dataset.cap, cam: target.dataset.cam === 'True' });
        }
        if (target.classList.contains('btn-del-room')) {
            if (confirm('Xóa phòng học này?')) apiCall(`${BASE}/room/${id}`, 'DELETE', {}, () => location.reload());
        }
        if (target.classList.contains('btn-set-current-sem')) {
            if (confirm('Đặt làm Học kỳ hiện tại?')) apiCall(`${BASE}/semester/${id}/set_current`, 'POST', {}, () => location.reload());
        }
        if (target.classList.contains('btn-del-sem')) {
            if (confirm('Xóa học kỳ này?')) apiCall(`${BASE}/semester/${id}`, 'DELETE', {}, () => location.reload());
        }

        // Schedule
        if (target.id === 'btn-view-schedule') openScheduleEditor();
        if (target.id === 'btn-add-sch-row') addScheduleRow();
        if (target.id === 'btn-save-schedules') saveSchedules();
        if (target.classList.contains('btn-remove-sch')) removeSchedule(target.dataset.index);
    });
});

// --- SCHEDULE LOGIC ---
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
    const wd = document.getElementById('sch-weekday').value;
    const ps = document.getElementById('sch-start-period');
    const pid = ps.value, pname = ps.options[ps.selectedIndex]?.text;
    const np = document.getElementById('sch-num-periods').value;
    const rs = document.getElementById('sch-room');
    const rid = rs.value, rname = rs.options[rs.selectedIndex]?.text;
    if (!wd || !pid || !np || !rid) { alert('Vui lòng điền đủ thông tin!'); return; }
    currentSchedules.push({ weekday: parseInt(wd), start_period_id: parseInt(pid), period_name: pname.split('(')[0].trim(), num_periods: parseInt(np), room_id: parseInt(rid), room_name: rname });
    renderSchedules();
}

function removeSchedule(i) { currentSchedules.splice(i, 1); renderSchedules(); }

function saveSchedules() {
    if (!currentClassId) return;
    if (!confirm('Hệ thống sẽ kiểm tra trùng lịch. Tiếp tục?')) return;
    fetch(`${BASE}/class/${currentClassId}/schedules`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ schedules: currentSchedules }) })
    .then(r => r.json()).then(d => { alert(d.message); if (d.status === 'success') document.getElementById('schedule-editor').style.display = 'none'; });
}
