/* === SYSTEM MANAGEMENT LOGIC === */
const BASE_ADMIN = '/admin';
const BASE_ACADEMIC = '/admin/academic';
let modalAction = null, modalId = null;

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
    
    // Lưu tab hiện tại vào localStorage
    localStorage.setItem('activeTabSystem', id);
}

function showModal(type, id = null, data = {}) {
    modalAction = type;
    modalId = id;
    let opts = "";
    const overlay = document.getElementById('modal-overlay');
    const body = document.getElementById('modal-body');
    const title = document.getElementById('modal-title');

    if (type === 'lecturer') {
        title.textContent = id ? 'Sửa Giảng viên' : 'Thêm Giảng viên';
        body.innerHTML = `
            <div class="form-group"><label>Tên đăng nhập</label><input type="text" id="m-user" value="${data.username || ''}" class="form-control"></div>
            <div class="form-group"><label>Họ tên</label><input type="text" id="m-name" value="${data.name || ''}" class="form-control"></div>
            <div class="form-group"><label>Mã GV</label><input type="text" id="m-code" value="${data.code || ''}" class="form-control"></div>
            <div class="form-group"><label>Mật khẩu ${id ? '(Để trống nếu không đổi)' : ''}</label><input type="password" id="m-pass" class="form-control"></div>`;
    } else if (type === 'class') {
        title.textContent = id ? 'Sửa Lớp học' : 'Thêm Lớp học';
        body.innerHTML = `
            <div class="form-group"><label>Tên lớp</label><input type="text" id="m-name" value="${data.name || ''}" class="form-control"></div>
            <div class="form-group"><label>Mã lớp</label><input type="text" id="m-code" value="${data.code || ''}" class="form-control"></div>`;
    } else if (type === 'dept') {
        title.textContent = id ? 'Sửa Khoa' : 'Thêm Khoa';
        body.innerHTML = `<div class="form-group"><label>Tên Khoa</label><input type="text" id="m-name" value="${data.name || ''}" class="form-control"></div>`;
    } else if (type === 'major') {
        title.textContent = id ? 'Sửa Ngành' : 'Thêm Ngành';
        const names = getStaticData('data-depts-names');
        const ids = getStaticData('data-depts-ids');
        opts = ids.map((did, i) => `<option value="${did}" ${did == data.dept_id ? 'selected' : ''}>${names[i]}</option>`).join('');
        body.innerHTML = `<div class="form-group"><label>Tên Ngành</label><input type="text" id="m-name" value="${data.name || ''}" class="form-control"></div>
        <div class="form-group"><label>Thuộc Khoa</label><select id="m-dept" class="form-control"><option value="">--Chọn Khoa--</option>${opts}</select></div>`;
    } else if (type === 'course') {
        title.textContent = id ? 'Sửa Học phần' : 'Thêm Học phần';
        const names = getStaticData('data-majors-names');
        const ids = getStaticData('data-majors-ids');
        opts = ids.map((mid, i) => `<option value="${mid}" ${mid == data.major_id ? 'selected' : ''}>${names[i]}</option>`).join('');
        body.innerHTML = `<div class="form-group"><label>Tên Học phần</label><input type="text" id="m-name" value="${data.name || ''}" class="form-control"></div>
        <div class="form-group"><label>Thuộc Ngành</label><select id="m-major" class="form-control"><option value="">--Chọn Ngành--</option>${opts}</select></div>`;
    } else if (type === 'view-students') {
        title.textContent = `Danh sách sinh viên - ${data.class_name}`;
        const rows = data.students.map(s => `<tr><td>${s.id}</td><td>${s.name}</td><td>${s.dob || '-'}</td></tr>`).join('');
        body.innerHTML = `
            <div style="max-height: 400px; overflow-y: auto;">
                <table style="width: 100%; font-size: 0.85rem;">
                    <thead><tr><th>MSSV</th><th>Họ tên</th><th>Ngày sinh</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="3" style="text-align:center;">Chưa có sinh viên</td></tr>'}</tbody>
                </table>
            </div>`;
        document.getElementById('btn-modal-save').style.display = 'none'; // Hide save button for view-only
    }
    overlay.style.display = 'flex';
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
        overlay.style.display = 'none';
        document.getElementById('btn-modal-save').style.display = 'block'; // Reset save button
    }
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
    if (!modalAction) return;
    const name = document.getElementById('m-name')?.value?.trim();

    if (modalAction === 'lecturer') {
        const username = document.getElementById('m-user').value;
        const code = document.getElementById('m-code').value;
        const password = document.getElementById('m-pass').value;
        const url = modalId ? `${BASE_ADMIN}/lecturer/${modalId}` : `${BASE_ADMIN}/lecturer`;
        apiCall(url, modalId ? 'PUT' : 'POST', { username, name, code, password }, () => location.reload());
    } else if (modalAction === 'class') {
        const code = document.getElementById('m-code').value;
        const url = modalId ? `${BASE_ADMIN}/class/${modalId}` : `${BASE_ADMIN}/class`;
        apiCall(url, modalId ? 'PUT' : 'POST', { name, code }, () => location.reload());
    } else if (modalAction === 'dept') {
        const url = modalId ? `${BASE_ACADEMIC}/department/${modalId}` : `${BASE_ACADEMIC}/department`;
        apiCall(url, modalId ? 'PUT' : 'POST', { name }, () => location.reload());
    } else if (modalAction === 'major') {
        const dept = document.getElementById('m-dept').value;
        apiCall(modalId ? `${BASE_ACADEMIC}/major/${modalId}` : `${BASE_ACADEMIC}/major`, modalId ? 'PUT' : 'POST', { name, department_id: parseInt(dept) }, () => location.reload());
    } else if (modalAction === 'course') {
        const major = document.getElementById('m-major').value;
        apiCall(modalId ? `${BASE_ACADEMIC}/course/${modalId}` : `${BASE_ACADEMIC}/course`, modalId ? 'PUT' : 'POST', { name, major_id: parseInt(major) }, () => location.reload());
    }
}

// --- EVENT LISTENERS ---
document.addEventListener('DOMContentLoaded', function() {
    // Khôi phục tab cũ từ localStorage
    const savedTab = localStorage.getItem('activeTabSystem');
    if (savedTab) switchTab(savedTab);

    document.addEventListener('click', function(e) {
        const target = e.target;
        if (target.classList.contains('tab-btn')) switchTab(target.dataset.tab);
        if (target.classList.contains('btn-add')) showModal(target.dataset.type);
        if (target.id === 'btn-modal-cancel' || target.id === 'modal-overlay') closeModal();
        if (target.id === 'btn-modal-save') saveModal();

        const id = target.dataset.id;
        // Edit/Delete Lecturer
        if (target.classList.contains('btn-edit-gv')) {
            showModal('lecturer', id, { username: target.dataset.user, name: target.dataset.name, code: target.dataset.code });
        }
        if (target.classList.contains('btn-del-gv')) {
            if (confirm('Xóa giảng viên này?')) apiCall(`${BASE_ADMIN}/lecturer/${id}`, 'DELETE', {}, () => location.reload());
        }
        // Edit/Delete Class
        if (target.classList.contains('btn-edit-cls')) {
            showModal('class', id, { name: target.dataset.name, code: target.dataset.code });
        }
        if (target.classList.contains('btn-del-cls')) {
            if (confirm('Xóa lớp học này?')) apiCall(`${BASE_ADMIN}/class/${id}`, 'DELETE', {}, () => location.reload());
        }
        // View Students Action
        if (target.classList.contains('btn-view-students')) {
            fetch(`${BASE_ADMIN}/class/${id}/students`)
                .then(r => r.json())
                .then(d => {
                    if (d.status === 'success') showModal('view-students', null, d);
                });
        }
        // Academic Catalog Actions (Moved from academic.js)
        if (target.classList.contains('btn-edit-dept')) showModal('dept', id, { name: target.dataset.name });
        if (target.classList.contains('btn-del-dept')) {
            if (confirm('Xóa Khoa này?')) apiCall(`${BASE_ACADEMIC}/department/${id}`, 'DELETE', {}, () => location.reload());
        }
        if (target.classList.contains('btn-edit-major')) showModal('major', id, { name: target.dataset.name, dept_id: target.dataset.dept });
        if (target.classList.contains('btn-del-major')) {
            if (confirm('Xóa Ngành này?')) apiCall(`${BASE_ACADEMIC}/major/${id}`, 'DELETE', {}, () => location.reload());
        }
        if (target.classList.contains('btn-edit-course')) showModal('course', id, { name: target.dataset.name, major_id: target.dataset.major });
        if (target.classList.contains('btn-del-course')) {
            if (confirm('Xóa Học phần này?')) apiCall(`${BASE_ACADEMIC}/course/${id}`, 'DELETE', {}, () => location.reload());
        }
    });

    // Excel Import
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('import-excel')) {
            const input = e.target;
            if (!input.files.length) return;
            const fd = new FormData();
            fd.append('file', input.files[0]);
            const type = input.dataset.type;
            const url = (type === 'students') ? '/admin/import/students' : `${BASE_ACADEMIC}/import/${type}`;
            fetch(url, { method: 'POST', body: fd })
                .then(r => r.json())
                .then(d => { alert(d.message); if (d.status === 'success') location.reload(); });
            input.value = '';
        }
    });
});
