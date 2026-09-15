import os
import sys
import unittest
import csv
import json
import shutil
import tempfile
from datetime import datetime, timedelta

# Add repository root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.experiment_logger import ExperimentLogger
from paper_experiments.analyzer.analyzer import ExperimentAnalyzer

class TestExperimentLoggerAndAnalyzer(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for raw experiment logs during testing
        ExperimentLogger._instance = None
        self.test_dir = tempfile.mkdtemp(prefix="test_experiments_")
        self.logger = ExperimentLogger(base_dir=self.test_dir)
        self.analyzer = ExperimentAnalyzer(base_dir=self.test_dir)

    def tearDown(self):
        # Clean up temporary test directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_1_normal_checkin_request(self):
        """Test 1: Ghi nhận 1 request điểm danh bình thường -> Tạo record trong CSV"""
        exp_id = self.logger.log_request(
            session_id="SESS_001",
            class_id="CLASS_101",
            predicted_identity="21D14801030160",
            similarity_score=0.75,
            match_threshold=0.65,
            recognition_accepted=True,
            recognition_result="SUCCESS",
            liveness_score=0.92,
            liveness_threshold=0.60,
            liveness_result=True,
            authorization_result=True,
            attendance_action="IN",
            attendance_status="SUCCESS",
            latency_total_ms=450.0,
            latency_liveness_ms=4.0,
            latency_face_recognition_ms=210.0,
            latency_matching_ms=0.6
        )

        self.assertIsNotNone(exp_id)
        self.assertTrue(os.path.exists(self.logger.log_csv_path))
        self.assertTrue(os.path.exists(self.logger.resource_csv_path))

        with open(self.logger.log_csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["experiment_id"], exp_id)
            self.assertEqual(rows[0]["similarity_score"], "0.75")
            self.assertEqual(rows[0]["attendance_status"], "SUCCESS")

    def test_2_multiple_consecutive_requests(self):
        """Test 2: Nhiều request liên tiếp -> Không bị ghi đè dữ liệu, ID là duy nhất"""
        exp_ids = []
        for i in range(5):
            exp_id = self.logger.log_request(
                session_id=f"SESS_{i}",
                predicted_identity=f"STUDENT_{i}",
                similarity_score=0.70 + (i * 0.02),
                attendance_status="SUCCESS",
                latency_total_ms=400.0 + (i * 10)
            )
            exp_ids.append(exp_id)

        self.assertEqual(len(set(exp_ids)), 5)

        with open(self.logger.log_csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 5)
            for idx, r in enumerate(rows):
                self.assertEqual(r["experiment_id"], exp_ids[idx])

    def test_3_restart_logger_preserves_raw_data(self):
        """Test 3: Restart SmartAttendance / Re-init Logger -> Data cũ không bị ghi đè"""
        self.logger.log_request(predicted_identity="STUDENT_BEFORE_RESTART")
        
        # Simulate app restart by instantiating logger again
        new_logger = ExperimentLogger(base_dir=self.test_dir)
        new_logger.log_request(predicted_identity="STUDENT_AFTER_RESTART")

        with open(self.logger.log_csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["predicted_identity"], "STUDENT_BEFORE_RESTART")
            self.assertEqual(rows[1]["predicted_identity"], "STUDENT_AFTER_RESTART")

    def test_4_and_5_same_day_and_date_range_filtering(self):
        """Test 4, 5, 6: Lọc dữ liệu theo ngày chính xác (Same-day & Date Range)"""
        # Inject records on specific dates into CSV
        with open(self.logger.log_csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Record 1: 2026-09-09
            writer.writerow(["exp_1", "2026-09-09 10:00:00.000", "2026-09-09", "10:00:00", "S1", "C1", "N/A", "S1", "0.7", "0.65", "True", "SUCCESS", "0.9", "0.6", "True", "Live", "True", "IN", "SUCCESS", "500", "4", "200", "1", "False"])
            # Record 2: 2026-09-10
            writer.writerow(["exp_2", "2026-09-10 14:30:00.000", "2026-09-10", "14:30:00", "S1", "C1", "N/A", "S2", "0.8", "0.65", "True", "SUCCESS", "0.9", "0.6", "True", "Live", "True", "IN", "SUCCESS", "480", "4", "190", "1", "False"])
            # Record 3: 2026-09-15
            writer.writerow(["exp_3", "2026-09-15 09:15:00.000", "2026-09-15", "09:15:00", "S1", "C1", "N/A", "S3", "0.85", "0.65", "True", "SUCCESS", "0.9", "0.6", "True", "Live", "True", "IN", "SUCCESS", "460", "4", "185", "1", "False"])
            # Record 4: 2026-09-21
            writer.writerow(["exp_4", "2026-09-21 16:00:00.000", "2026-09-21", "16:00:00", "S1", "C1", "N/A", "S4", "0.75", "0.65", "True", "SUCCESS", "0.9", "0.6", "True", "Live", "True", "IN", "SUCCESS", "510", "4", "205", "1", "False"])

        # Test 5: Same day filter (2026-09-10 -> 2026-09-10)
        report_same_day = self.analyzer.analyze(start_date="2026-09-10", end_date="2026-09-10", exclude_warmup=False)
        self.assertEqual(report_same_day["performance"]["total_latency_ms"]["n"], 1)

        # Test 6: Range filter (2026-09-10 -> 2026-09-20)
        report_range = self.analyzer.analyze(start_date="2026-09-10", end_date="2026-09-20", exclude_warmup=False)
        self.assertEqual(report_range["performance"]["total_latency_ms"]["n"], 2)  # Should pick Sept 10 and Sept 15 only!

    def test_7_insufficient_ground_truth_handling(self):
        """Test 7: Thiếu ground truth -> Không được bịa số liệu, báo INSUFFICIENT_GROUND_TRUTH"""
        self.logger.log_request(
            expected_identity="N/A",  # No ground truth
            predicted_identity="STUDENT_X",
            similarity_score=0.78,
            attendance_status="SUCCESS"
        )

        today_str = datetime.now().strftime("%Y-%m-%d")
        report = self.analyzer.analyze(start_date=today_str, end_date=today_str, exclude_warmup=False)
        self.assertEqual(report["recognition"]["status"], "INSUFFICIENT_GROUND_TRUTH")
        self.assertEqual(report["antispoof"]["status"], "INSUFFICIENT_GROUND_TRUTH")

    def test_8_failed_request_recording(self):
        """Test 8: Request thất bại (Ví dụ bị Spoof hoặc No Face) -> Ghi nhận đúng trạng thái lỗi"""
        exp_id = self.logger.log_request(
            predicted_identity=None,
            similarity_score=-1.0,
            liveness_score=0.15,
            liveness_result=False,
            attack_type="Print-attack",
            recognition_accepted=False,
            recognition_result="SPOOF_ATTACK",
            attendance_status="REJECTED",
            latency_total_ms=350.0
        )

        with open(self.logger.log_csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["recognition_result"], "SPOOF_ATTACK")
            self.assertEqual(rows[0]["attendance_status"], "REJECTED")

if __name__ == "__main__":
    unittest.main()
