/* === ACADEMIC MANAGEMENT LOGIC === */
const WEEKDAY_MAP = { 2: 'Thứ 2', 3: 'Thứ 3', 4: 'Thứ 4', 5: 'Thứ 5', 6: 'Thứ 6', 7: 'Thứ 7', 8: 'Chủ Nhật' };
const BASE = '/admin/academic';
let modalAction = null, modalId = null;
let currentClassId = null, currentSchedules = [];

function formatDateVN(dateStr) {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length !== 3) return '';
    const year = parts[0];
    const month = parseInt(parts[1]);
    const day = parseInt(parts[2]);
    return `Ngày ${day} tháng ${month} năm ${year}`;
}

function updateDatePreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    if (input && preview) {
        const val = input.value;
        if (val) {
            preview.innerText = '👉 Xác nhận: ' + formatDateVN(val);
        } else {
            preview.innerText = '';
        }
    }
}

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
    
    if (id === 'tab-makeup') loadMakeupRequests();
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
        <div class="form-group">
            <label>Ngày bắt đầu</label>
            <input type="date" id="m-start" value="${data.start || ''}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;" oninput="updateDatePreview('m-start', 'start-preview')">
            <span id="start-preview" style="font-size: 13px; color: #4338ca; font-weight: bold; margin-top: 4px; display: block;"></span>
        </div>
        <div class="form-group">
            <label>Ngày kết thúc</label>
            <input type="date" id="m-end" value="${data.end || ''}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;" oninput="updateDatePreview('m-end', 'end-preview')">
            <span id="end-preview" style="font-size: 13px; color: #4338ca; font-weight: bold; margin-top: 4px; display: block;"></span>
        </div>`;
        setTimeout(() => {
            updateDatePreview('m-start', 'start-preview');
            updateDatePreview('m-end', 'end-preview');
        }, 50);
    } else if (type === 'room') {
        title.textContent = id ? 'Sửa Phòng học' : 'Thêm Phòng học';
        body.innerHTML = `<div class="form-group"><label>Tên phòng</label><input type="text" id="m-name" value="${data.name || ''}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label>Sức chứa</label><input type="number" id="m-cap" value="${data.cap || 50}" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div class="form-group"><label><input type="checkbox" id="m-cam" ${data.cam ? 'checked' : ''}> Có Camera nhận diện</label></div>`;
    } else if (type === 'holiday') {
        title.textContent = 'Thêm Ngày nghỉ / Lễ';
        body.innerHTML = `<div class="form-group"><label>Tên ngày lễ</label><input type="text" id="m-name" placeholder="VD: Nghỉ Tết" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
            <div class="form-group">
                <label>Từ ngày</label>
                <input type="date" id="m-date" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;" oninput="updateDatePreview('m-date', 'holiday-start-preview')">
                <span id="holiday-start-preview" style="font-size: 13px; color: #4338ca; font-weight: bold; margin-top: 4px; display: block;"></span>
            </div>
            <div class="form-group">
                <label>Đến ngày</label>
                <input type="date" id="m-end-date" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;" oninput="updateDatePreview('m-end-date', 'holiday-end-preview')">
                <span id="holiday-end-preview" style="font-size: 13px; color: #4338ca; font-weight: bold; margin-top: 4px; display: block;"></span>
            </div>
        </div>`;
        setTimeout(() => {
            updateDatePreview('m-date', 'holiday-start-preview');
            updateDatePreview('m-end-date', 'holiday-end-preview');
        }, 50);
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
            .then(r => r.json()).then(d => { 
                alert(d.message); 
                if (d.status === 'success') { 
                    closeModal(); 
                    loadSessions(currentClassId); // Tải lại danh sách buổi học sau khi lưu
                } 
            });
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
        const tabBtn = target.closest('.tab-btn');
        if (tabBtn) switchTab(tabBtn.dataset.tab);
        const btnAdd = target.closest('.btn-add');
        if (btnAdd) showModal(btnAdd.dataset.type);

        if (target.id === 'btn-modal-cancel') closeModal();
        if (target.id === 'btn-modal-save') saveModal();

        const btnEditSem = target.closest('.btn-edit-sem');
        if (btnEditSem) showModal('semester', btnEditSem.dataset.id, { name: btnEditSem.dataset.name, start: btnEditSem.dataset.start, end: btnEditSem.dataset.end });
        
        const btnEditRoom = target.closest('.btn-edit-room');
        if (btnEditRoom) showModal('room', btnEditRoom.dataset.id, { name: btnEditRoom.dataset.name, cap: btnEditRoom.dataset.cap, cam: btnEditRoom.dataset.cam === 'True' });
        
        const btnDelRoom = target.closest('.btn-del-room');
        if (btnDelRoom) { if (confirm('Xóa phòng học này?')) apiCall(`${BASE}/room/${btnDelRoom.dataset.id}`, 'DELETE', {}, () => location.reload()); }
        
        const btnSetCurrentSem = target.closest('.btn-set-current-sem');
        if (btnSetCurrentSem) { if (confirm('Đặt làm Học kỳ hiện tại?')) apiCall(`${BASE}/semester/${btnSetCurrentSem.dataset.id}/set_current`, 'POST', {}, () => location.reload()); }
        
        const btnDelSem = target.closest('.btn-del-sem');
        if (btnDelSem) { if (confirm('Xóa học kỳ này?')) apiCall(`${BASE}/semester/${btnDelSem.dataset.id}`, 'DELETE', {}, () => location.reload()); }
        
        if (target.id === 'btn-view-schedule') openScheduleEditor();
        if (target.id === 'btn-add-sch-row') addScheduleRow();
        if (target.id === 'btn-save-schedules') saveSchedules();
        
        const btnRemoveSch = target.closest('.btn-remove-sch');
        if (btnRemoveSch) removeSchedule(btnRemoveSch.dataset.index);
        
        if (target.id === 'btn-recalculate-sessions') recalculateSessions();
        
        const btnDelCourse = target.closest('.btn-del-course');
        if (btnDelCourse) { if (confirm('Xóa học phần này?')) apiCall(`${BASE}/course/${btnDelCourse.dataset.id}`, 'DELETE', {}, () => location.reload()); }
        
        const btnDelHoliday = target.closest('.btn-del-holiday');
        if (btnDelHoliday) { if (confirm('Xóa ngày nghỉ này?')) apiCall(`${BASE}/holiday/${btnDelHoliday.dataset.id}`, 'DELETE', {}, () => location.reload()); }
    });
});

function openScheduleEditor() {
    const id = document.getElementById('class-select').value;
    if (!id) { alert('Chọn lớp trước!'); return; }
    currentClassId = id;
    document.getElementById('schedule-editor').style.display = 'block';
    fetch(`${BASE}/class/${id}/schedules`).then(r => r.json()).then(d => { currentSchedules = d; renderSchedules(); });
    loadSessions(id); // Tải danh sách buổi học thực tế
}

function loadSessions(classId) {
    const container = document.getElementById('session-list-container');
    const tbody = document.getElementById('session-tbody');
    const badge = document.getElementById('session-count-badge');
    
    container.style.display = 'block';
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;">Đang tải danh sách buổi học...</td></tr>';
    
    fetch(`${BASE}/class/${classId}/sessions`)
        .then(r => r.json())
        .then(sessions => {
            badge.textContent = `${sessions.length} buổi học`;
            if (sessions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:#888;">Chưa có buổi học nào được sinh ra cho lớp này.</td></tr>';
                return;
            }
            
            tbody.innerHTML = sessions.map(s => {
                const date = new Date(s.session_date);
                const wd = WEEKDAY_MAP[date.getDay() + 1] || s.session_date;
                let statusStyle = 'color:#666;';
                let statusText = s.status;
                
                if (s.status === 'SCHEDULED') {
                    statusText = 'Chờ dạy';
                    statusStyle = 'color:#007bff;font-weight:bold;';
                } else if (s.status === 'COMPLETED') {
                    statusText = 'Hoàn thành';
                    statusStyle = 'color:#28a745;font-weight:bold;';
                } else if (s.status === 'HOLIDAY') {
                    statusText = 'Nghỉ lễ';
                    statusStyle = 'color:#ff9800;font-weight:bold;';
                }
                
                return `
                    <tr style="border-bottom:1px solid #f5f5f5;">
                        <td style="padding:10px;"><strong>${s.session_date}</strong></td>
                        <td style="padding:10px;">${wd}</td>
                        <td style="padding:10px;">${s.start_time} - ${s.end_time}</td>
                        <td style="padding:10px;">${s.room_name || s.room || '---'}</td>
                        <td style="padding:10px;text-align:center;">${s.num_periods}</td>
                        <td style="padding:10px;text-align:center;${statusStyle}">${statusText}</td>
                    </tr>
                `;
            }).join('');
        })
        .catch(err => {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:red;">Lỗi tải dữ liệu buổi học.</td></tr>';
        });
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

function loadMakeupRequests() {
    const tbodyPending = document.getElementById('makeup-requests-tbody');
    const tbodyProcessed = document.getElementById('makeup-processed-tbody');
    
    if (tbodyPending) {
        tbodyPending.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;">Đang tải danh sách...</td></tr>';
        fetch(`${BASE}/makeup/pending`)
        .then(r => r.json())
        .then(requests => {
            if (requests.length === 0) {
                tbodyPending.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:#888;">Chưa có yêu cầu dạy bù nào đang chờ duyệt.</td></tr>';
                return;
            }
            
            tbodyPending.innerHTML = requests.map(m => `
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding:12px 10px;"><strong>${m.lecturer_name}</strong></td>
                    <td style="padding:12px 10px;">${m.class_name}</td>
                    <td style="padding:12px 10px;"><code>${m.requested_date}</code></td>
                    <td style="padding:12px 10px;">${m.period_name} - <strong>${m.room_name}</strong></td>
                    <td style="padding:12px 10px;"><small>${m.reason || '---'}</small></td>
                    <td style="padding:12px 10px; text-align:right;">
                        <button class="btn btn-success btn-sm" onclick="handleMakeup(${m.id}, 'APPROVED')">Duyệt</button>
                        <button class="btn btn-danger btn-sm" onclick="handleMakeup(${m.id}, 'REJECTED')">Từ chối</button>
                    </td>
                </tr>
            `).join('');
        });
    }

    if (tbodyProcessed) {
        tbodyProcessed.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px;">Đang tải lịch sử...</td></tr>';
        fetch(`${BASE}/makeup/processed`)
        .then(r => r.json())
        .then(requests => {
            if (requests.length === 0) {
                tbodyProcessed.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#888;">Chưa có đơn dạy bù nào được xử lý.</td></tr>';
                return;
            }
            
            tbodyProcessed.innerHTML = requests.map(m => {
                const isApproved = (m.status === 'APPROVED');
                const badge = isApproved 
                    ? '<span style="background: #dcfce7; color: #15803d; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-circle-check"></i> Đã duyệt</span>'
                    : '<span style="background: #fee2e2; color: #b91c1c; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-circle-xmark"></i> Từ chối</span>';
                
                return `
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding:12px 10px;"><strong>${m.lecturer_name}</strong></td>
                        <td style="padding:12px 10px;">${m.class_name}</td>
                        <td style="padding:12px 10px;"><code>${m.requested_date}</code></td>
                        <td style="padding:12px 10px;">${m.period_name} - <strong>${m.room_name}</strong></td>
                        <td style="padding:12px 10px;"><small>${m.reason || '---'}</small></td>
                        <td style="padding:12px 10px;"><small style="color: #64748b;">${m.approver_name || 'Admin'}</small></td>
                        <td style="padding:12px 10px; text-align:center;">${badge}</td>
                    </tr>
                `;
            }).join('');
        });
    }
}

function handleMakeup(reqId, status) {
    if (!confirm(`Bạn có chắc chắn muốn ${status === 'APPROVED' ? 'DUYỆT' : 'TỪ CHỐI'} yêu cầu này?`)) return;
    
    fetch(`${BASE}/makeup/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: reqId, status: status })
    })
    .then(r => r.json())
    .then(data => {
        alert(data.message);
        loadMakeupRequests();
    });
}

function addScheduleRow() {
    const wd = document.getElementById('sch-weekday').value, ps = document.getElementById('sch-start-period'), np = document.getElementById('sch-num-periods').value, rs = document.getElementById('sch-room');
    const pid = ps.value, pname = ps.options[ps.selectedIndex]?.text, rid = rs.value, rname = rs.options[rs.selectedIndex]?.text;
    if (!wd || !pid || !np || !rid) { alert('Vui lòng điền đủ thông tin!'); return; }
    
    // Validation: Kiểm tra tràn tiết (Giả định tối đa 10 tiết, có thể cải tiến bằng cách lấy động)
    if (parseInt(pid) + parseInt(np) - 1 > 12) {
        alert(`Lỗi: Tiết bắt đầu (${pid}) cộng với ${np} tiết học sẽ vượt quá số tiết tối đa trong ngày (12 tiết).`);
        return;
    }

    // Senior Engineer Block Validation
    function getBlock(pId) {
        if (pId >= 1 && pId <= 4) return "Sáng";
        if (pId >= 5 && pId <= 8) return "Chiều";
        if (pId >= 9 && pId <= 12) return "Tối";
        return "Khác";
    }
    const startBlock = getBlock(parseInt(pid));
    const endBlock = getBlock(parseInt(pid) + parseInt(np) - 1);
    if (startBlock !== endBlock) {
        alert(`Lỗi: Lịch học không được vượt quá ranh giới buổi (Tiết ${pid} là buổi ${startBlock}, tiết kết thúc là buổi ${endBlock}). Vui lòng chọn số tiết phù hợp.`);
        return;
    }

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
