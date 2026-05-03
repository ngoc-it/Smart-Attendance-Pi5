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
        const cNames = getStaticData('data-courses-names');
        const cIds = getStaticData('data-courses-ids');
        const cCodes = getStaticData('data-courses-codes');
        opts = cIds.map((cid, i) => `<option value="${cid}" ${cid == data.course_id ? 'selected' : ''}>${cCodes[i]} - ${cNames[i]}</option>`).join('');

        body.innerHTML = `
            <div class="form-group"><label>Tên lớp</label><input type="text" id="m-name" value="${data.name || ''}" class="form-control"></div>
            <div class="form-group"><label>Mã lớp</label><input type="text" id="m-code" value="${data.code || ''}" class="form-control"></div>
            <div class="form-group"><label>Thuộc Học phần</label><select id="m-course" class="form-control"><option value="">--Chọn Học phần (Để sinh TKB)--</option>${opts}</select></div>`;
    } else if (type === 'assign-lecturer') {
        title.textContent = `Phân công giảng viên - ${data.class_name}`;
        const gvNames = getStaticData('data-lecturers-names') || [];
        const gvIds = getStaticData('data-lecturers-ids') || [];
        opts = gvIds.map((gid, i) => `<option value="${gid}">${gvNames[i]}</option>`).join('');
        
        body.innerHTML = `
            <div class="form-group">
                <label>Chọn giảng viên giảng dạy:</label>
                <select id="m-lecturer-id" class="form-control">
                    <option value="">-- Chọn giảng viên --</option>
                    ${opts}
                </select>
            </div>
            <p style="font-size:0.8rem;color:#666;">💡 Thao tác này sẽ gán lớp học phần cho giảng viên được chọn.</p>
        `;
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
        const mNames = getStaticData('data-majors-names');
        const mIds = getStaticData('data-majors-ids');
        opts = mIds.map((mid, i) => `<option value="${mid}" ${mid == data.major_id ? 'selected' : ''}>${mNames[i]}</option>`).join('');
        
        body.innerHTML = `
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                <div class="form-group"><label>Mã HP</label><input type="text" id="m-code" value="${data.code || ''}" class="form-control"></div>
                <div class="form-group"><label>Tên Học phần</label><input type="text" id="m-name" value="${data.name || ''}" class="form-control"></div>
            </div>
            <div class="form-group">
                <label>Khối kiến thức</label>
                <select id="m-cat" class="form-control">
                    <option value="">-- Chưa phân loại --</option>
                    <option value="Đại cương" ${data.cat == 'Đại cương' ? 'selected' : ''}>Kiến thức đại cương</option>
                    <option value="Cơ sở ngành" ${data.cat == 'Cơ sở ngành' ? 'selected' : ''}>Kiến thức cơ sở ngành</option>
                    <option value="Chuyên ngành" ${data.cat == 'Chuyên ngành' ? 'selected' : ''}>Kiến thức chuyên ngành</option>
                    <option value="Tốt nghiệp" ${data.cat == 'Tốt nghiệp' ? 'selected' : ''}>Kiến thức tốt nghiệp</option>
                </select>
            </div>
            <div class="form-group"><label>Thuộc Ngành</label><select id="m-major" class="form-control"><option value="">-- Dùng chung (Đại cương) --</option>${opts}</select></div>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px;">
                <div class="form-group"><label>Số TC</label><input type="number" id="m-credits" value="${data.credits || 0}" class="form-control"></div>
                <div class="form-group"><label>TC Lý thuyết</label><input type="number" id="m-lt" value="${data.lt || 0}" class="form-control"></div>
                <div class="form-group"><label>TC Thực hành</label><input type="number" id="m-th" value="${data.th || 0}" class="form-control"></div>
            </div>
            <div class="form-group"><label>Tổng số tiết (Tự động tính nếu để 0)</label><input type="number" id="m-periods" value="${data.periods || 0}" class="form-control"></div>`;
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
        document.getElementById('btn-modal-save').style.display = 'none';
    }
    overlay.style.display = 'flex';

    if (type === 'course') {
        const inpLT = document.getElementById('m-lt');
        const inpTH = document.getElementById('m-th');
        const inpCredits = document.getElementById('m-credits');
        const inpPeriods = document.getElementById('m-periods');
        const updateAuto = () => {
            const lt = parseInt(inpLT.value) || 0;
            const th = parseInt(inpTH.value) || 0;
            inpCredits.value = lt + th;
            inpPeriods.value = (lt * 15) + (th * 30);
        };
        inpLT.addEventListener('input', updateAuto);
        inpTH.addEventListener('input', updateAuto);
    }
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
        overlay.style.display = 'none';
        document.getElementById('btn-modal-save').style.display = 'block';
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
        const course_id = document.getElementById('m-course').value;
        const url = modalId ? `${BASE_ADMIN}/class/${modalId}` : `${BASE_ADMIN}/class`;
        apiCall(url, modalId ? 'PUT' : 'POST', { name, code, course_id: course_id ? parseInt(course_id) : null }, () => location.reload());
    } else if (modalAction === 'assign-lecturer') {
        const userId = document.getElementById('m-lecturer-id').value;
        if (!userId) { alert('Vui lòng chọn giảng viên!'); return; }
        apiCall(`${BASE_ADMIN}/lecturer/assign`, 'POST', { user_id: parseInt(userId), class_id: modalId }, () => {
            alert('Phân công thành công!');
            location.reload();
        });
    } else if (modalAction === 'dept') {
        const url = modalId ? `${BASE_ACADEMIC}/department/${modalId}` : `${BASE_ACADEMIC}/department`;
        apiCall(url, modalId ? 'PUT' : 'POST', { name }, () => location.reload());
    } else if (modalAction === 'major') {
        const dept = document.getElementById('m-dept').value;
        apiCall(modalId ? `${BASE_ACADEMIC}/major/${modalId}` : `${BASE_ACADEMIC}/major`, modalId ? 'PUT' : 'POST', { name, department_id: parseInt(dept) }, () => location.reload());
    } else if (modalAction === 'course') {
        const major = document.getElementById('m-major').value;
        const code = document.getElementById('m-code').value;
        const cat = document.getElementById('m-cat').value;
        const credits = parseInt(document.getElementById('m-credits').value) || 0;
        const lt_credits = parseInt(document.getElementById('m-lt').value) || 0;
        const th_credits = parseInt(document.getElementById('m-th').value) || 0;
        const total_periods = parseInt(document.getElementById('m-periods').value) || 0;
        apiCall(modalId ? `${BASE_ACADEMIC}/course/${modalId}` : `${BASE_ACADEMIC}/course`, modalId ? 'PUT' : 'POST', { name, code, major_id: major ? parseInt(major) : null, category: cat, credits, lt_credits, th_credits, total_periods }, () => location.reload());
    }
}

// --- EVENT LISTENERS ---
document.addEventListener('DOMContentLoaded', function() {
    const savedTab = localStorage.getItem('activeTabSystem');
    if (savedTab) switchTab(savedTab);

    document.addEventListener('click', function(e) {
        const target = e.target;
        if (target.classList.contains('tab-btn')) switchTab(target.dataset.tab);
        if (target.classList.contains('btn-add')) showModal(target.dataset.type);
        if (target.id === 'btn-modal-cancel' || target.id === 'modal-overlay') closeModal();
        if (target.id === 'btn-modal-save') saveModal();

        const id = target.dataset.id;
        if (target.classList.contains('btn-edit-gv')) {
            showModal('lecturer', id, { username: target.dataset.user, name: target.dataset.name, code: target.dataset.code });
        }
        if (target.classList.contains('btn-del-gv')) {
            if (confirm('Xóa giảng viên này?')) apiCall(`${BASE_ADMIN}/lecturer/${id}`, 'DELETE', {}, () => location.reload());
        }
        if (target.classList.contains('btn-edit-cls')) {
            showModal('class', id, { name: target.dataset.name, code: target.dataset.code, course_id: target.dataset.course });
        }
        if (target.classList.contains('btn-del-cls')) {
            if (confirm('Xóa lớp học này?')) apiCall(`${BASE_ADMIN}/class/${id}`, 'DELETE', {}, () => location.reload());
        }
        if (target.classList.contains('btn-view-students')) {
            fetch(`${BASE_ADMIN}/class/${id}/students`).then(r => r.json()).then(d => {
                if (d.status === 'success') showModal('view-students', null, d);
            });
        }
        if (target.classList.contains('btn-assign-lecturer')) {
            showModal('assign-lecturer', id, { class_name: target.dataset.name });
        }
        if (target.classList.contains('btn-edit-dept')) showModal('dept', id, { name: target.dataset.name });
        if (target.classList.contains('btn-del-dept')) {
            if (confirm('Xóa Khoa này?')) apiCall(`${BASE_ACADEMIC}/department/${id}`, 'DELETE', {}, () => location.reload());
        }
        if (target.classList.contains('btn-edit-major')) showModal('major', id, { name: target.dataset.name, dept_id: target.dataset.dept });
        if (target.classList.contains('btn-del-major')) {
            if (confirm('Xóa Ngành này?')) apiCall(`${BASE_ACADEMIC}/major/${id}`, 'DELETE', {}, () => location.reload());
        }
        if (target.classList.contains('btn-edit-course')) {
            showModal('course', id, { name: target.dataset.name, code: target.dataset.code, credits: target.dataset.credits, lt: target.dataset.lt, th: target.dataset.th, periods: target.dataset.periods, cat: target.dataset.cat, major_id: target.dataset.major });
        }
        if (target.classList.contains('btn-del-course')) {
            if (confirm('Xóa Học phần này?')) apiCall(`${BASE_ACADEMIC}/course/${id}`, 'DELETE', {}, () => location.reload());
        }
    });

    const filterMajor = document.getElementById('filter-course-major');
    const filterCat = document.getElementById('filter-course-category');
    function filterCourses() {
        const majorVal = filterMajor.value, catVal = filterCat.value;
        document.querySelectorAll('.course-row').forEach(row => {
            const rowMajor = row.dataset.major, rowCat = row.dataset.category;
            const matchMajor = !majorVal || rowMajor == majorVal, matchCat = !catVal || rowCat == catVal;
            row.style.display = (matchMajor && matchCat) ? '' : 'none';
        });
    }
    if (filterMajor) filterMajor.onchange = filterCourses;
    if (filterCat) filterCat.onchange = filterCourses;

    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('import-excel')) {
            const input = e.target;
            if (!input.files.length) return;
            const fd = new FormData();
            fd.append('file', input.files[0]);
            const type = input.dataset.type;
            const url = (type === 'students') ? '/admin/import/students' : `${BASE_ACADEMIC}/import/${type}`;
            fetch(url, { method: 'POST', body: fd }).then(r => r.json()).then(d => { alert(d.message); if (d.status === 'success') location.reload(); });
            input.value = '';
        }
    });

    const btnImportCurriculum = document.getElementById('btn-import-curriculum');
    const importArea = document.getElementById('import-area');
    const btnCancelImport = document.getElementById('btn-cancel-import');
    const btnDoImport = document.getElementById('btn-do-import');
    if (btnImportCurriculum) btnImportCurriculum.onclick = () => importArea.style.display = 'block';
    if (btnCancelImport) btnCancelImport.onclick = () => importArea.style.display = 'none';
    if (btnDoImport) {
        btnDoImport.onclick = () => {
            const fileInput = document.getElementById('curriculum-file');
            if (fileInput.files.length === 0) { alert('Chọn file trước!'); return; }
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            btnDoImport.disabled = true;
            btnDoImport.textContent = 'Đang xử lý...';
            fetch(`${BASE_ACADEMIC}/import/curriculum`, { method: 'POST', body: formData }).then(r => r.json()).then(d => { alert(d.message); if (d.status === 'success') location.reload(); }).catch(err => alert('Lỗi kết nối!')).finally(() => { btnDoImport.disabled = false; btnDoImport.textContent = 'Tải lên & Xử lý'; });
        };
    }
});
