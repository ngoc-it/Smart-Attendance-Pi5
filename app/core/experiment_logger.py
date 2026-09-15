import os
import sys
import time
import uuid
import json
import csv
import threading
import platform
import subprocess
from datetime import datetime
import psutil

class ExperimentLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ExperimentLogger, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, base_dir=None):
        with self._lock:
            if base_dir is None:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                target_base_dir = os.path.abspath(os.path.join(current_dir, "../../experiments"))
            else:
                target_base_dir = base_dir

            if self._initialized and getattr(self, "base_dir", None) == target_base_dir:
                return

            self.base_dir = target_base_dir
            self.raw_dir = os.path.join(self.base_dir, "raw")
            self.config_dir = os.path.join(self.base_dir, "config")
            self.results_dir = os.path.join(self.base_dir, "results")
            self.reports_dir = os.path.join(self.base_dir, "reports")

            for d in [self.raw_dir, self.config_dir, self.results_dir, self.reports_dir]:
                os.makedirs(d, exist_ok=True)

            self.log_csv_path = os.path.join(self.raw_dir, "experiment_log.csv")
            self.resource_csv_path = os.path.join(self.raw_dir, "resource_samples.csv")
            self.config_json_path = os.path.join(self.config_dir, "experiment_config.json")

            self._boot_time = datetime.now()
            self._request_counter = 0
            self._warmup_limit = 2

            self._init_csv_headers()
            self._init_config_json()
            
            self._initialized = True
            print(f"[ExperimentLogger] Initialized successfully. Raw data path: {self.raw_dir}")

    def _init_csv_headers(self):
        """Khởi tạo tiêu đề CSV nếu tệp chưa tồn tại (Bảo toàn raw data khi restart)"""
        log_headers = [
            "experiment_id",
            "timestamp",
            "date",
            "time",
            "session_id",
            "class_id",
            "expected_identity",
            "predicted_identity",
            "similarity_score",
            "match_threshold",
            "recognition_accepted",
            "recognition_result",
            "liveness_score",
            "liveness_threshold",
            "liveness_result",
            "attack_type",
            "authorization_result",
            "attendance_action",
            "attendance_status",
            "latency_total_ms",
            "latency_liveness_ms",
            "latency_face_recognition_ms",
            "latency_matching_ms",
            "is_warmup"
        ]

        resource_headers = [
            "experiment_id",
            "timestamp",
            "process_cpu_percent",
            "process_memory_mb",
            "system_cpu_percent",
            "system_memory_percent",
            "peak_cpu_percent",
            "peak_memory_mb"
        ]

        if not os.path.exists(self.log_csv_path):
            with open(self.log_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(log_headers)

        if not os.path.exists(self.resource_csv_path):
            with open(self.resource_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(resource_headers)

    def _init_config_json(self):
        """Khởi tạo tệp mô tả cấu hình phần cứng, phần mềm và AI models"""
        git_commit = "unknown"
        try:
            repo_root = os.path.abspath(os.path.join(self.base_dir, ".."))
            git_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
        except Exception:
            pass

        import cv2
        import onnxruntime as ort
        import insightface

        config_data = {
            "system_info": {
                "device": "Raspberry Pi 5" if os.path.exists("/proc/device-tree/model") else platform.node(),
                "camera": "Sony IMX708 Camera Module 3",
                "os": platform.platform(),
                "python_version": sys.version.split()[0],
                "git_commit": git_commit
            },
            "library_versions": {
                "opencv": cv2.__version__,
                "onnxruntime": ort.__version__,
                "insightface": insightface.__version__
            },
            "ai_models": {
                "face_recognition_model": "InsightFace buffalo_l (w600k_r50.onnx)",
                "face_embedding_dimension": 512,
                "liveness_model": "MiniFASNetV2 ONNX",
                "face_detector": "YOLOv11 / InsightFace det_10g"
            },
            "experiment_setup": {
                "logger_version": "1.0.0",
                "boot_timestamp": self._boot_time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        with open(self.config_json_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)

    def log_request(
        self,
        session_id=None,
        class_id=None,
        expected_identity=None,
        predicted_identity=None,
        similarity_score=None,
        match_threshold=0.65,
        recognition_accepted=False,
        recognition_result="REJECTED",
        liveness_score=None,
        liveness_threshold=0.60,
        liveness_result=False,
        attack_type=None,
        authorization_result=False,
        attendance_action="NONE",
        attendance_status="REJECTED",
        latency_total_ms=0.0,
        latency_liveness_ms=0.0,
        latency_face_recognition_ms=0.0,
        latency_matching_ms=0.0,
        cpu_samples=None,
        ram_samples=None
    ):
        """Ghi lại 1 bản ghi thực nghiệm raw hoàn chỉnh mà không làm ảnh hưởng đến luồng chính"""
        try:
            now = datetime.now()
            experiment_id = f"exp_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

            with self._lock:
                self._request_counter += 1
                is_warmup = (self._request_counter <= self._warmup_limit)

            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S.%f")[:-3]
            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            log_row = [
                experiment_id,
                timestamp_str,
                date_str,
                time_str,
                session_id if session_id is not None else "N/A",
                class_id if class_id is not None else "N/A",
                expected_identity if expected_identity is not None else "N/A",
                predicted_identity if predicted_identity is not None else "N/A",
                round(float(similarity_score), 4) if similarity_score is not None else "N/A",
                round(float(match_threshold), 4),
                bool(recognition_accepted),
                str(recognition_result),
                round(float(liveness_score), 4) if liveness_score is not None else "N/A",
                round(float(liveness_threshold), 4),
                bool(liveness_result),
                attack_type if attack_type is not None else "N/A",
                bool(authorization_result),
                str(attendance_action),
                str(attendance_status),
                round(float(latency_total_ms), 2),
                round(float(latency_liveness_ms), 2),
                round(float(latency_face_recognition_ms), 2),
                round(float(latency_matching_ms), 2),
                bool(is_warmup)
            ]

            # Đo đạc tài nguyên CPU / RAM hiện tại
            process = psutil.Process(os.getpid())
            proc_cpu = process.cpu_percent(interval=None)
            proc_mem_mb = process.memory_info().rss / (1024 * 1024)
            sys_cpu = psutil.cpu_percent(interval=None)
            sys_mem = psutil.virtual_memory().percent

            peak_cpu = max(cpu_samples) if (cpu_samples and len(cpu_samples) > 0) else proc_cpu
            peak_mem = max(ram_samples) if (ram_samples and len(ram_samples) > 0) else proc_mem_mb

            resource_row = [
                experiment_id,
                timestamp_str,
                round(proc_cpu, 2),
                round(proc_mem_mb, 2),
                round(sys_cpu, 2),
                round(sys_mem, 2),
                round(peak_cpu, 2),
                round(peak_mem, 2)
            ]

            # Append an toàn vào tệp CSV
            with self._lock:
                with open(self.log_csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(log_row)

                with open(self.resource_csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(resource_row)

            return experiment_id
        except Exception as e:
            # Ghi log cảnh báo ra console, tuyệt đối KHÔNG throw exception ra ngoài luồng ứng dụng
            print(f"[ExperimentLogger WARNING] Failed to record experiment log: {e}")
            return None

def get_experiment_logger():
    return ExperimentLogger()
