# SMARTATTENDANCE EXPERIMENTAL ANALYSIS REPORT

- **Query Date Range**: `2026-09-01` to `2026-09-18`
- **Total Records Analyzed**: `45`
- **Excluded Warm-up Requests**: `True`

## 1. Performance & Latency Metrics

| Metric | Mean (ms) | Median (ms) | Min (ms) | Max (ms) | Std (ms) | P90 (ms) | P95 (ms) | P99 (ms) |
|---|---|---|---|---|---|---|---|---|
| Total Transaction Latency | 1110.4 | 1040.68 | 686.25 | 1771.45 | 210.42 | 1340.33 | 1522.54 | 1675.34 |
| Face Recognition Latency | 1096.17 | 1031.53 | 683.35 | 1768.92 | 212.52 | 1326.97 | 1518.46 | 1669.34 |
| Liveness Check Latency | 6.45 | 5.75 | 0.0 | 23.35 | 4.99 | 12.88 | 15.42 | 20.46 |
| Database Matching Latency | 0.01 | 0.0 | 0.0 | 0.04 | 0.01 | 0.03 | 0.03 | 0.04 |

### Hardware Resource Consumption

- **Average CPU Usage**: `0.0%` (Peak: `39.2%`)
- **Average RAM Memory**: `895.32 MB` (Peak: `1025.88 MB`)

## 2. Recognition Metrics

> **INFO**: Insufficient ground-truth data (expected_identity is not assigned in raw logs).

## 3. Anti-Spoofing Metrics

- **APCER**: `0.0%`
- **BPCER**: `0.0%`

