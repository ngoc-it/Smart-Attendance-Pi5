import os
import sys
import argparse
import json
import csv
from datetime import datetime
import numpy as np

class ExperimentAnalyzer:
    def __init__(self, base_dir=None):
        if base_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.abspath(os.path.join(current_dir, "../../experiments"))

        self.base_dir = base_dir
        self.raw_dir = os.path.join(self.base_dir, "raw")
        self.results_dir = os.path.join(self.base_dir, "results")
        os.makedirs(self.results_dir, exist_ok=True)

        self.log_csv = os.path.join(self.raw_dir, "experiment_log.csv")
        self.resource_csv = os.path.join(self.raw_dir, "resource_samples.csv")
        self.config_json = os.path.join(self.base_dir, "config", "experiment_config.json")

    def parse_datetime(self, dt_str):
        """Parse datetime string supporting multiple formats"""
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                pass
        raise ValueError(f"Cannot parse datetime string: '{dt_str}'")

    def load_data(self, start_date_str, end_date_str, exclude_warmup=True):
        """Lọc dữ liệu chính xác theo khoảng thời gian [start_date 00:00:00, end_date 23:59:59]"""
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        if not os.path.exists(self.log_csv):
            print(f"[Analyzer ERROR] Log file not found at: {self.log_csv}")
            return [], []

        raw_logs = []
        with open(self.log_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row_dt = self.parse_datetime(row["timestamp"])
                    if start_dt <= row_dt <= end_dt:
                        if exclude_warmup and row.get("is_warmup", "False").lower() in ("true", "1"):
                            continue
                        raw_logs.append(row)
                except Exception:
                    continue

        resource_map = {}
        if os.path.exists(self.resource_csv):
            with open(self.resource_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    resource_map[row["experiment_id"]] = row

        filtered_resources = []
        for log in raw_logs:
            exp_id = log["experiment_id"]
            if exp_id in resource_map:
                filtered_resources.append(resource_map[exp_id])

        return raw_logs, filtered_resources

    def analyze(self, start_date, end_date, exclude_warmup=True):
        logs, resources = self.load_data(start_date, end_date, exclude_warmup=exclude_warmup)
        n_samples = len(logs)

        report = {
            "query_range": {
                "start_date": start_date,
                "end_date": end_date,
                "exclude_warmup": exclude_warmup,
                "n_samples": n_samples
            },
            "performance": {},
            "recognition": {},
            "antispoof": {}
        }

        if n_samples == 0:
            report["status"] = "NO_DATA_IN_RANGE"
            report["message"] = f"No experiment logs found between {start_date} and {end_date}."
            return report

        report["status"] = "SUCCESS"

        # --- 1. PERFORMANCE METRICS ---
        total_latencies = [float(r["latency_total_ms"]) for r in logs if r.get("latency_total_ms")]
        liveness_latencies = [float(r["latency_liveness_ms"]) for r in logs if r.get("latency_liveness_ms")]
        recognition_latencies = [float(r["latency_face_recognition_ms"]) for r in logs if r.get("latency_face_recognition_ms")]
        matching_latencies = [float(r["latency_matching_ms"]) for r in logs if r.get("latency_matching_ms")]

        def calc_stats(arr):
            if not arr:
                return {"n": 0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "std": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
            a = np.array(arr)
            return {
                "n": len(a),
                "mean": round(float(np.mean(a)), 2),
                "median": round(float(np.median(a)), 2),
                "min": round(float(np.min(a)), 2),
                "max": round(float(np.max(a)), 2),
                "std": round(float(np.std(a)), 2),
                "p90": round(float(np.percentile(a, 90)), 2),
                "p95": round(float(np.percentile(a, 95)), 2),
                "p99": round(float(np.percentile(a, 99)), 2)
            }

        cpu_avg_list = [float(res["process_cpu_percent"]) for res in resources if res.get("process_cpu_percent")]
        cpu_peak_list = [float(res["peak_cpu_percent"]) for res in resources if res.get("peak_cpu_percent")]
        ram_avg_list = [float(res["process_memory_mb"]) for res in resources if res.get("process_memory_mb")]
        ram_peak_list = [float(res["peak_memory_mb"]) for res in resources if res.get("peak_memory_mb")]

        report["performance"] = {
            "total_latency_ms": calc_stats(total_latencies),
            "liveness_latency_ms": calc_stats(liveness_latencies),
            "face_recognition_latency_ms": calc_stats(recognition_latencies),
            "matching_latency_ms": calc_stats(matching_latencies),
            "hardware_resources": {
                "avg_cpu_percent": round(float(np.mean(cpu_avg_list)), 2) if cpu_avg_list else 0.0,
                "peak_cpu_percent": round(float(np.max(cpu_peak_list)), 2) if cpu_peak_list else 0.0,
                "avg_ram_mb": round(float(np.mean(ram_avg_list)), 2) if ram_avg_list else 0.0,
                "peak_ram_mb": round(float(np.max(ram_peak_list)), 2) if ram_peak_list else 0.0
            }
        }

        # --- 2. RECOGNITION METRICS ---
        valid_rec_samples = [r for r in logs if r.get("expected_identity") and r["expected_identity"] != "N/A"]

        if len(valid_rec_samples) == 0:
            report["recognition"] = {
                "status": "INSUFFICIENT_GROUND_TRUTH",
                "message": "Insufficient ground-truth data (expected_identity is not assigned in raw logs)."
            }
        else:
            tp = sum(1 for r in valid_rec_samples if r["expected_identity"] == r["predicted_identity"] and r["recognition_result"] == "SUCCESS")
            fp = sum(1 for r in valid_rec_samples if r["expected_identity"] != r["predicted_identity"] and r["recognition_accepted"].lower() == "true")
            tn = sum(1 for r in valid_rec_samples if r["expected_identity"] != r["predicted_identity"] and r["recognition_accepted"].lower() == "false")
            fn = sum(1 for r in valid_rec_samples if r["expected_identity"] == r["predicted_identity"] and r["recognition_result"] != "SUCCESS")

            acc = (tp + tn) / len(valid_rec_samples) if len(valid_rec_samples) > 0 else 0.0
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            far = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            frr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

            report["recognition"] = {
                "status": "VALID",
                "n_samples": len(valid_rec_samples),
                "accuracy": round(acc * 100.0, 2),
                "precision": round(prec * 100.0, 2),
                "recall": round(rec * 100.0, 2),
                "f1_score": round(f1 * 100.0, 2),
                "far": round(far * 100.0, 4),
                "frr": round(frr * 100.0, 4)
            }

        # --- 3. ANTI-SPOOFING METRICS ---
        spoof_logs = [r for r in logs if r.get("attack_type") and r["attack_type"] != "N/A"]

        if len(spoof_logs) == 0:
            report["antispoof"] = {
                "status": "INSUFFICIENT_GROUND_TRUTH",
                "message": "Insufficient ground-truth data for Liveness evaluation."
            }
        else:
            attacks = [r for r in spoof_logs if r["attack_type"] in ("Print-attack", "Replay-attack")]
            bonafides = [r for r in spoof_logs if r["attack_type"] == "Live"]

            apcer = (sum(1 for r in attacks if r["liveness_result"].lower() == "true") / len(attacks)) * 100.0 if attacks else 0.0
            bpcer = (sum(1 for r in bonafides if r["liveness_result"].lower() == "false") / len(bonafides)) * 100.0 if bonafides else 0.0

            report["antispoof"] = {
                "status": "VALID",
                "n_attack_samples": len(attacks),
                "n_bonafide_samples": len(bonafides),
                "apcer_percent": round(apcer, 2),
                "bpcer_percent": round(bpcer, 2)
            }

        self._export_results(report)
        return report

    def _export_results(self, report):
        """Xuất các báo cáo dạng JSON, Markdown và CSV"""
        # Save JSON
        json_path = os.path.join(self.results_dir, "summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)

        # Save Markdown
        md_path = os.path.join(self.results_dir, "summary.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# SMARTATTENDANCE EXPERIMENTAL ANALYSIS REPORT\n\n")
            q = report["query_range"]
            f.write(f"- **Query Date Range**: `{q['start_date']}` to `{q['end_date']}`\n")
            f.write(f"- **Total Records Analyzed**: `{q['n_samples']}`\n")
            f.write(f"- **Excluded Warm-up Requests**: `{q['exclude_warmup']}`\n\n")

            if report.get("status") == "NO_DATA_IN_RANGE":
                f.write("> **WARNING**: No raw experiment data records found within the specified date range.\n")
                return

            f.write("## 1. Performance & Latency Metrics\n\n")
            f.write("| Metric | Mean (ms) | Median (ms) | Min (ms) | Max (ms) | Std (ms) | P90 (ms) | P95 (ms) | P99 (ms) |\n")
            f.write("|---|---|---|---|---|---|---|---|---|\n")

            perf = report["performance"]
            for key, name in [
                ("total_latency_ms", "Total Transaction Latency"),
                ("face_recognition_latency_ms", "Face Recognition Latency"),
                ("liveness_latency_ms", "Liveness Check Latency"),
                ("matching_latency_ms", "Database Matching Latency")
            ]:
                s = perf[key]
                f.write(f"| {name} | {s['mean']} | {s['median']} | {s['min']} | {s['max']} | {s['std']} | {s['p90']} | {s['p95']} | {s['p99']} |\n")

            hw = perf["hardware_resources"]
            f.write("\n### Hardware Resource Consumption\n\n")
            f.write(f"- **Average CPU Usage**: `{hw['avg_cpu_percent']}%` (Peak: `{hw['peak_cpu_percent']}%`)\n")
            f.write(f"- **Average RAM Memory**: `{hw['avg_ram_mb']} MB` (Peak: `{hw['peak_ram_mb']} MB`)\n\n")

            f.write("## 2. Recognition Metrics\n\n")
            rec = report["recognition"]
            if rec["status"] == "INSUFFICIENT_GROUND_TRUTH":
                f.write(f"> **INFO**: {rec['message']}\n\n")
            else:
                f.write(f"- **Accuracy**: `{rec['accuracy']}%`\n")
                f.write(f"- **Precision**: `{rec['precision']}%`\n")
                f.write(f"- **Recall**: `{rec['recall']}%`\n")
                f.write(f"- **F1-Score**: `{rec['f1_score']}`\n")
                f.write(f"- **FAR (False Acceptance Rate)**: `{rec['far']}%`\n")
                f.write(f"- **FRR (False Rejection Rate)**: `{rec['frr']}%`\n\n")

            f.write("## 3. Anti-Spoofing Metrics\n\n")
            anti = report["antispoof"]
            if anti["status"] == "INSUFFICIENT_GROUND_TRUTH":
                f.write(f"> **INFO**: {anti['message']}\n\n")
            else:
                f.write(f"- **APCER**: `{anti['apcer_percent']}%`\n")
                f.write(f"- **BPCER**: `{anti['bpcer_percent']}%`\n\n")

        # Save Performance CSV
        perf_csv = os.path.join(self.results_dir, "performance_results.csv")
        with open(perf_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Mean_ms", "Median_ms", "Min_ms", "Max_ms", "Std_ms", "P90_ms", "P95_ms", "P99_ms"])
            for key, name in [
                ("total_latency_ms", "Total Latency"),
                ("face_recognition_latency_ms", "Face Recognition"),
                ("liveness_latency_ms", "Liveness Check"),
                ("matching_latency_ms", "Matching")
            ]:
                s = report["performance"][key]
                writer.writerow([name, s['mean'], s['median'], s['min'], s['max'], s['std'], s['p90'], s['p95'], s['p99']])

def main():
    parser = argparse.ArgumentParser(description="SmartAttendance Experimental Data Analyzer")
    parser.add_argument("--start-date", required=True, help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End Date (YYYY-MM-DD)")
    parser.add_argument("--include-warmup", action="store_true", help="Include warm-up requests in statistics")
    args = parser.parse_args()

    analyzer = ExperimentAnalyzer()
    report = analyzer.analyze(
        start_date=args.start_date,
        end_date=args.end_date,
        exclude_warmup=not args.include_warmup
    )

    print("=" * 65)
    print(" SMARTATTENDANCE EXPERIMENT ANALYSIS RESULTS")
    print("=" * 65)
    print(f"Date Range: {args.start_date} -> {args.end_date}")
    print(f"Status    : {report.get('status')}")
    if report.get("status") == "SUCCESS":
        perf = report["performance"]["total_latency_ms"]
        hw = report["performance"]["hardware_resources"]
        print(f"Samples N : {perf['n']}")
        print(f"Mean Latency : {perf['mean']} ms (P95: {perf['p95']} ms)")
        print(f"CPU Avg/Peak : {hw['avg_cpu_percent']}% / {hw['peak_cpu_percent']}%")
        print(f"RAM Avg/Peak : {hw['avg_ram_mb']} MB / {hw['peak_ram_mb']} MB")
        print(f"Recognition  : {report['recognition'].get('status')}")
        print(f"Anti-Spoofing: {report['antispoof'].get('status')}")
        print(f"\nReport saved to: {os.path.join(analyzer.results_dir, 'summary.md')}")
    else:
        print(f"Message   : {report.get('message')}")
    print("=" * 65)

if __name__ == "__main__":
    main()
