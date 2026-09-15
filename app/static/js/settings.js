/* === SETTINGS PAGE LOGIC === */

document.addEventListener('DOMContentLoaded', function() {
    const settingsForm = document.getElementById('settings-form');
    
    if (settingsForm) {
        settingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            // UI Feedback
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerText;
            submitBtn.disabled = true;
            submitBtn.innerText = "Đang lưu...";

            fetch('/admin/settings/update', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'success') {
                    alert(data.message);
                    location.reload();
                } else {
                    alert("Lỗi: " + data.message);
                    submitBtn.disabled = false;
                    submitBtn.innerText = originalText;
                }
            })
            .catch(err => {
                alert("Lỗi kết nối!");
                submitBtn.disabled = false;
                submitBtn.innerText = originalText;
            });
        });
    }

    // Camera status polling (optional enhancement)
    const statusDot = document.querySelector('.camera-status-dot');
    if (statusDot) {
        // Here you could add a real-time health check if endpoint exists
    }
});

// Helper for range input display
function updateThresholdDisplay(val) {
    const output = document.getElementById('threshold-output');
    if (output) output.value = val;
}

function updateLivenessDisplay(val) {
    const output = document.getElementById('liveness-output');
    if (output) output.value = val;
}

