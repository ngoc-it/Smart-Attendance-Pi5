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
    const content = document.getElementById(id);
    if (!content) return;

    document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    content.style.display = 'block';

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
    } else if (type === 'student') {
        title.textContent = id ? 'Sửa Sinh viên' : 'Thêm Sinh viên';
        body.innerHTML = `
            <div class="form-group"><label>MSSV (Mã số sinh viên)</label><input type="text" id="m-std-id" value="${id || ''}" ${id ? 'disabled' : ''} class="form-control"></div>
            <div class="form-group"><label>Họ tên</label><input type="text" id="m-name" value="${data.name || ''}" class="form-control"></div>
            <div class="form-group"><label>Ngày sinh (DD/MM/YYYY)</label><input type="text" id="m-dob" value="${data.dob || ''}" placeholder="Ví dụ: 12/03/2004" class="form-control"></div>
            <div class="form-group"><label>Lớp sinh hoạt</label><input type="text" id="m-std-class" value="${data.class || ''}" class="form-control"></div>`;
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
        const currentLecturerId = data.lecturer_id ? String(data.lecturer_id).split(',')[0] : '';
        opts = gvIds.map((gid, i) => `<option value="${gid}" ${String(gid) === currentLecturerId ? 'selected' : ''}>${gvNames[i]}</option>`).join('');

        body.innerHTML = `
            <div class="form-group">
                <label>Chọn giảng viên giảng dạy:</label>
                <select id="m-lecturer-id" class="form-control">
                    <option value="">-- Chưa phân công / Hủy phân công --</option>
                    ${opts}
                </select>
            </div>
            <p style="font-size:0.8rem;color:#666;">💡 Chọn giảng viên để gán quyền quản lý lớp học phần này, hoặc chọn "Hủy phân công" để gỡ bỏ.</p>
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
        const rows = data.students.map(s => `
            <tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.15s;">
                <td style="padding: 12px 14px; font-weight: 500; color: #1e293b;">${s.id}</td>
                <td style="padding: 12px 14px; font-weight: 600; color: #0f172a;">${s.name}</td>
                <td style="padding: 12px 14px; color: #64748b;">${s.dob || '-'}</td>
                <td style="padding: 12px 14px; text-align: right;">
                    <button class="btn-action-subtle btn-remove-class-student" data-class-id="${data.class_id}" data-student-id="${s.id}" style="color: #dc2626; border: 1px solid #fecaca; background: #fef2f2; padding: 6px 12px; font-size: 0.8rem; border-radius: 6px; font-weight: 600; cursor: pointer;" title="Loại sinh viên khỏi lớp này">
                        <i class="fa-solid fa-user-minus"></i> Loại
                    </button>
                </td>
            </tr>`).join('');
        body.innerHTML = `
            <div style="max-height: 480px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 10px;">
                <table style="width: 100%; font-size: 0.9rem; border-collapse: collapse; text-align: left;">
                    <thead style="position: sticky; top: 0; background: #f8fafc; border-bottom: 2px solid #cbd5e1; z-index: 2;">
                        <tr>
                            <th style="padding: 12px 14px; color: #475569; font-weight: 700;">MSSV</th>
                            <th style="padding: 12px 14px; color: #475569; font-weight: 700;">HỌ TÊN</th>
                            <th style="padding: 12px 14px; color: #475569; font-weight: 700;">NGÀY SINH</th>
                            <th style="padding: 12px 14px; color: #475569; font-weight: 700; text-align: right;">THAO TÁC</th>
                        </tr>
                    </thead>
                    <tbody>${rows || '<tr><td colspan="4" style="text-align:center; padding: 24px; color: #94a3b8;">Chưa có sinh viên trong lớp này</td></tr>'}</tbody>
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
        .then(async r => {
            const d = await r.json().catch(() => ({ status: 'error', message: 'Lỗi phản hồi từ máy chủ (HTTP ' + r.status + ')' }));
            if (r.ok && d.status === 'success') {
                closeModal();
                if (onSuccess) onSuccess();
            } else {
                alert('Lỗi: ' + (d.message || 'Thao tác không thành công'));
            }
        })
        .catch(err => alert('Lỗi kết nối server: ' + (err.message || 'Không thể gửi yêu cầu')));
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
    } else if (modalAction === 'student') {
        const student_id = document.getElementById('m-std-id').value.trim();
        const dob = document.getElementById('m-dob').value.trim();
        const student_class = document.getElementById('m-std-class').value.trim();
        if (!student_id || !name) { alert('MSSV và Họ tên là bắt buộc!'); return; }
        const url = modalId ? `${BASE_ADMIN}/student/${modalId}` : `${BASE_ADMIN}/student`;
        apiCall(url, modalId ? 'PUT' : 'POST', { student_id, name, dob, student_class }, () => location.reload());
    } else if (modalAction === 'class') {

        const code = document.getElementById('m-code').value;
        const course_id = document.getElementById('m-course').value;
        const url = modalId ? `${BASE_ADMIN}/class/${modalId}` : `${BASE_ADMIN}/class`;
        apiCall(url, modalId ? 'PUT' : 'POST', { name, code, course_id: course_id ? parseInt(course_id) : null }, () => location.reload());
    } else if (modalAction === 'assign-lecturer') {
        const userId = document.getElementById('m-lecturer-id').value;
        apiCall(`${BASE_ADMIN}/lecturer/assign`, 'POST', { user_id: userId ? parseInt(userId) : null, class_id: parseInt(modalId) }, () => {
            alert('Cập nhật phân công giảng viên thành công!');
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
document.addEventListener('DOMContentLoaded', function () {
    const savedTab = localStorage.getItem('activeTabSystem');
    if (savedTab) switchTab(savedTab);

    document.addEventListener('click', function (e) {
        const target = e.target;
        const tabBtn = target.closest('.tab-btn');
        if (tabBtn) switchTab(tabBtn.dataset.tab);

        const btnAdd = target.closest('.btn-add');
        if (btnAdd) showModal(btnAdd.dataset.type);

        if (target.id === 'btn-modal-cancel') closeModal();
        if (target.id === 'btn-modal-save') saveModal();

        const btnEditGv = target.closest('.btn-edit-gv');
        if (btnEditGv) {
            showModal('lecturer', btnEditGv.dataset.id, { username: btnEditGv.dataset.user, name: btnEditGv.dataset.name, code: btnEditGv.dataset.code });
        }
        const btnDelGv = target.closest('.btn-del-gv');
        if (btnDelGv) {
            if (confirm('Xóa giảng viên này?')) apiCall(`${BASE_ADMIN}/lecturer/${btnDelGv.dataset.id}`, 'DELETE', {}, () => location.reload());
        }
        const btnEditStd = target.closest('.btn-edit-std');
        if (btnEditStd) {
            showModal('student', btnEditStd.dataset.id, { name: btnEditStd.dataset.name, dob: btnEditStd.dataset.dob, class: btnEditStd.dataset.class });
        }
        const btnDelStd = target.closest('.btn-del-std');
        if (btnDelStd) {
            if (confirm('Ngưng hoạt động sinh viên này? (Dữ liệu cũ vẫn được giữ nguyên)')) {
                apiCall(`${BASE_ADMIN}/student/${btnDelStd.dataset.id}`, 'DELETE', {}, () => location.reload());
            }
        }
        const btnEditCls = target.closest('.btn-edit-cls');
        if (btnEditCls) {
            showModal('class', btnEditCls.dataset.id, { name: btnEditCls.dataset.name, code: btnEditCls.dataset.code, course_id: btnEditCls.dataset.course });
        }
        const btnDelCls = target.closest('.btn-del-cls');
        if (btnDelCls) {
            if (confirm('Xóa lớp học này?')) apiCall(`${BASE_ADMIN}/class/${btnDelCls.dataset.id}`, 'DELETE', {}, () => location.reload());
        }

        const btnViewStudents = target.closest('.btn-view-students');
        if (btnViewStudents) {
            const classId = btnViewStudents.dataset.id;
            fetch(`${BASE_ADMIN}/class/${classId}/students`)
                .then(r => r.json())
                .then(d => {
                    if (d.status === 'success') {
                        showModal('view-students', null, d);
                    } else {
                        alert('Lỗi: ' + (d.message || 'Không thể lấy danh sách sinh viên'));
                    }
                })
                .catch(err => {
                    alert('Lỗi kết nối khi lấy danh sách sinh viên!');
                });
        }
        const btnRemoveClassStudent = target.closest('.btn-remove-class-student');
        if (btnRemoveClassStudent) {
            const classId = btnRemoveClassStudent.dataset.classId;
            const studentId = btnRemoveClassStudent.dataset.studentId;
            if (confirm(`Loại sinh viên ${studentId} khỏi lớp học phần này?`)) {
                apiCall(`${BASE_ADMIN}/class/${classId}/student/${studentId}`, 'DELETE', {}, () => {
                    alert('Đã loại sinh viên khỏi lớp học phần thành công!');
                    location.reload();
                });
            }
        }
        const btnAssign = target.closest('.btn-assign-lecturer');
        if (btnAssign) {
            showModal('assign-lecturer', btnAssign.dataset.id, {
                class_name: btnAssign.dataset.name,
                lecturer_id: btnAssign.dataset.lecturerId
            });
        }
        const btnEditDept = target.closest('.btn-edit-dept');
        if (btnEditDept) showModal('dept', btnEditDept.dataset.id, { name: btnEditDept.dataset.name });
        
        const btnDelDept = target.closest('.btn-del-dept');
        if (btnDelDept) {
            if (confirm('Xóa Khoa này?')) apiCall(`${BASE_ACADEMIC}/department/${btnDelDept.dataset.id}`, 'DELETE', {}, () => location.reload());
        }
        const btnEditMajor = target.closest('.btn-edit-major');
        if (btnEditMajor) showModal('major', btnEditMajor.dataset.id, { name: btnEditMajor.dataset.name, dept_id: btnEditMajor.dataset.dept });
        
        const btnDelMajor = target.closest('.btn-del-major');
        if (btnDelMajor) {
            if (confirm('Xóa Ngành này?')) apiCall(`${BASE_ACADEMIC}/major/${btnDelMajor.dataset.id}`, 'DELETE', {}, () => location.reload());
        }
        const btnEditCourse = target.closest('.btn-edit-course');
        if (btnEditCourse) {
            showModal('course', btnEditCourse.dataset.id, { name: btnEditCourse.dataset.name, code: btnEditCourse.dataset.code, credits: btnEditCourse.dataset.credits, lt: btnEditCourse.dataset.lt, th: btnEditCourse.dataset.th, periods: btnEditCourse.dataset.periods, cat: btnEditCourse.dataset.cat, major_id: btnEditCourse.dataset.major });
        }
        const btnDelCourse = target.closest('.btn-del-course');
        if (btnDelCourse) {
            if (confirm('Xóa Học phần này?')) apiCall(`${BASE_ACADEMIC}/course/${btnDelCourse.dataset.id}`, 'DELETE', {}, () => location.reload());
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

    // Filters & Search for students (DB Level)
    const filterStudentDept = document.getElementById('filter-student-dept');
    const searchStudentDb = document.getElementById('search-student-db');
    const btnSearchStudent = document.getElementById('btn-search-student');

    function triggerStudentFilter() {
        const dept = filterStudentDept ? filterStudentDept.value : '';
        const q = searchStudentDb ? searchStudentDb.value.trim() : '';
        const url = new URL(window.location.href);
        url.searchParams.set('page_std', '1');
        if (dept) url.searchParams.set('dept_std', dept);
        else url.searchParams.delete('dept_std');
        if (q) url.searchParams.set('q_std', q);
        else url.searchParams.delete('q_std');
        window.location.href = url.toString();
    }

    if (filterStudentDept) filterStudentDept.onchange = triggerStudentFilter;
    if (btnSearchStudent) btnSearchStudent.onclick = triggerStudentFilter;
    if (searchStudentDb) {
        searchStudentDb.onkeydown = function (e) {
            if (e.key === 'Enter') triggerStudentFilter();
        };
    }


    document.addEventListener('change', function (e) {
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
