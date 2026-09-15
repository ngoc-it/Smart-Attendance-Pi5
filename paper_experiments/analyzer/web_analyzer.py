import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, send_file

# Import Analyzer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from paper_experiments.analyzer.analyzer import ExperimentAnalyzer

app = Flask(__name__)
analyzer = ExperimentAnalyzer()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartAttendance Experiment Analyzer</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --success: #22c55e;
            --warning: #f59e0b;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            padding: 20px 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
        }

        h1 {
            color: var(--accent);
            margin: 0 0 10px 0;
        }

        p.subtitle {
            color: var(--text-muted);
            margin: 0;
        }

        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .form-group {
            display: flex;
            gap: 20px;
            align-items: flex-end;
            flex-wrap: wrap;
        }

        .field {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        label {
            font-weight: 600;
            color: var(--text-muted);
            font-size: 0.9rem;
        }

        input[type="date"] {
            background-color: #0f172a;
            border: 1px solid var(--border);
            color: #fff;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 1rem;
            outline: none;
        }

        input[type="date"]:focus {
            border-color: var(--accent);
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 10px;
        }

        button.btn-analyze {
            background-color: var(--accent);
            color: #000;
            font-weight: 700;
            border: none;
            padding: 12px 28px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.2s ease;
        }

        button.btn-analyze:hover {
            background-color: var(--accent-hover);
            color: #fff;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }

        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }

        th {
            background-color: #0f172a;
            color: var(--accent);
            font-weight: 600;
        }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .badge-success { background-color: rgba(34, 197, 94, 0.2); color: var(--success); }
        .badge-warning { background-color: rgba(245, 158, 11, 0.2); color: var(--warning); }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }

        .metric-box {
            background-color: #0f172a;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid var(--border);
            text-align: center;
        }

        .metric-val {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--accent);
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>SmartAttendance Experiment Analyzer</h1>
            <p class="subtitle">Hệ thống Phân tích Dữ liệu Thực nghiệm Tự động (Date Range Filtered)</p>
        </header>

        <div class="card">
            <form id="analyze-form">
                <div class="form-group">
                    <div class="field">
                        <label for="start_date">Ngày bắt đầu (From Date):</label>
                        <input type="date" id="start_date" name="start_date" value="{{ default_start }}">
                    </div>

                    <div class="field">
                        <label for="end_date">Ngày kết thúc (To Date):</label>
                        <input type="date" id="end_date" name="end_date" value="{{ default_end }}">
                    </div>

                    <div class="field">
                        <button type="submit" class="btn-analyze">🔍 [ ANALYZE DATA ]</button>
                    </div>
                </div>

                <div class="checkbox-group">
                    <input type="checkbox" id="exclude_warmup" name="exclude_warmup" checked>
                    <label for="exclude_warmup">Bỏ qua các request Khởi động (Exclude Warm-up requests)</label>
                </div>
            </form>
        </div>

        <div id="results-section" style="display: none;">
            <div class="card">
                <h2>📈 TỔNG QUAN HIỆU NĂNG PHẦN CỨNG & ĐỘ TRỄ</h2>
                <div class="metrics-grid">
                    <div class="metric-box">
                        <div class="text-muted">Tổng mẫu N</div>
                        <div class="metric-val" id="m-n">0</div>
                    </div>
                    <div class="metric-box">
                        <div class="text-muted">Độ trễ trung bình (Mean)</div>
                        <div class="metric-val" id="m-mean">0 ms</div>
                    </div>
                    <div class="metric-box">
                        <div class="text-muted">Độ trễ P95</div>
                        <div class="metric-val" id="m-p95">0 ms</div>
                    </div>
                    <div class="metric-box">
                        <div class="text-muted">CPU Peak %</div>
                        <div class="metric-val" id="m-cpu">0%</div>
                    </div>
                    <div class="metric-box">
                        <div class="text-muted">RAM Peak MB</div>
                        <div class="metric-val" id="m-ram">0 MB</div>
                    </div>
                </div>

                <h3 style="margin-top: 25px;">Bảng Phân rã Độ trễ Kỹ thuật (Sub-stage Latency Breakdown)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Công đoạn đo</th>
                            <th>Mean (ms)</th>
                            <th>Median (ms)</th>
                            <th>Min (ms)</th>
                            <th>Max (ms)</th>
                            <th>Std (ms)</th>
                            <th>P95 (ms)</th>
                        </tr>
                    </thead>
                    <tbody id="latency-table-body">
                    </tbody>
                </table>
            </div>

            <div class="card">
                <h2>👤 CHỈ SỐ NHẬN DIỆN SINH TRÁC HỌC (RECOGNITION)</h2>
                <div id="rec-status-area"></div>
            </div>

            <div class="card">
                <h2>🛡️ CHỈ SỐ CHỐNG GIẢ MẠO (ANTI-SPOOFING / LIVENESS)</h2>
                <div id="anti-status-area"></div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('analyze-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            const startDate = document.getElementById('start_date').value;
            const endDate = document.getElementById('end_date').value;
            const excludeWarmup = document.getElementById('exclude_warmup').checked;

            const res = await fetch(`/api/analyze?start_date=${startDate}&end_date=${endDate}&exclude_warmup=${excludeWarmup}`);
            const data = await res.json();

            if (data.status === 'NO_DATA_IN_RANGE') {
                alert('Không có dữ liệu thực nghiệm nào trong khoảng ngày đã chọn!');
                document.getElementById('results-section').style.display = 'none';
                return;
            }

            document.getElementById('results-section').style.display = 'block';
            const perf = data.performance.total_latency_ms;
            const hw = data.performance.hardware_resources;

            document.getElementById('m-n').innerText = perf.n;
            document.getElementById('m-mean').innerText = perf.mean + ' ms';
            document.getElementById('m-p95').innerText = perf.p95 + ' ms';
            document.getElementById('m-cpu').innerText = hw.peak_cpu_percent + '%';
            document.getElementById('m-ram').innerText = hw.peak_ram_mb + ' MB';

            const tbody = document.getElementById('latency-table-body');
            tbody.innerHTML = '';
            
            const latencies = [
                { name: 'Tổng thời gian phản hồi (Total Transaction)', s: data.performance.total_latency_ms },
                { name: 'Phát hiện & Embedding (Face Recognition)', s: data.performance.face_recognition_latency_ms },
                { name: 'Chống giả mạo (MiniFASNetV2 Liveness)', s: data.performance.liveness_latency_ms },
                { name: 'So khớp Cosine & Truy vấn CSDL', s: data.performance.matching_latency_ms }
            ];

            latencies.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${item.name}</strong></td>
                    <td>${item.s.mean}</td>
                    <td>${item.s.median}</td>
                    <td>${item.s.min}</td>
                    <td>${item.s.max}</td>
                    <td>${item.s.std}</td>
                    <td><strong>${item.s.p95}</strong></td>
                `;
                tbody.appendChild(tr);
            });

            // Recognition Area
            const recArea = document.getElementById('rec-status-area');
            if (data.recognition.status === 'INSUFFICIENT_GROUND_TRUTH') {
                recArea.innerHTML = `<span class="badge badge-warning">INSUFFICIENT DATA</span> ${data.recognition.message}`;
            } else {
                const r = data.recognition;
                recArea.innerHTML = `
                    <p><span class="badge badge-success">VALID</span> (Mẫu N = ${r.n_samples})</p>
                    <ul>
                        <li>Accuracy: <strong>${r.accuracy}%</strong></li>
                        <li>Precision: <strong>${r.precision}%</strong></li>
                        <li>Recall: <strong>${r.recall}%</strong></li>
                        <li>F1-Score: <strong>${r.f1_score}%</strong></li>
                        <li>FAR: <strong>${r.far}%</strong></li>
                        <li>FRR: <strong>${r.frr}%</strong></li>
                    </ul>
                `;
            }

            // Anti-spoof Area
            const antiArea = document.getElementById('anti-status-area');
            if (data.antispoof.status === 'INSUFFICIENT_GROUND_TRUTH') {
                antiArea.innerHTML = `<span class="badge badge-warning">INSUFFICIENT DATA</span> ${data.antispoof.message}`;
            } else {
                const a = data.antispoof;
                antiArea.innerHTML = `
                    <p><span class="badge badge-success">VALID</span></p>
                    <ul>
                        <li>APCER: <strong>${a.apcer_percent}%</strong> (Attack samples: ${a.n_attack_samples})</li>
                        <li>BPCER: <strong>${a.bpcer_percent}%</strong> (Bonafide samples: ${a.n_bonafide_samples})</li>
                    </ul>
                `;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    today = datetime.now()
    default_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    default_end = today.strftime("%Y-%m-%d")
    return render_template_string(HTML_TEMPLATE, default_start=default_start, default_end=default_end)

@app.route('/api/analyze')
def analyze_api():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    exclude_warmup = request.args.get('exclude_warmup', 'true').lower() == 'true'

    if not start_date or not end_date:
        return jsonify({"status": "ERROR", "message": "Missing start_date or end_date"}), 400

    report = analyzer.analyze(start_date, end_date, exclude_warmup=exclude_warmup)
    return jsonify(report)

if __name__ == '__main__':
    port = 5001
    print("\n" + "=" * 60)
    print(f" SMARTATTENDANCE WEB ANALYZER IS RUNNING ON http://localhost:{port}")
    print("=" * 60 + "\n")
    app.run(host='0.0.0.0', port=port, debug=False)
