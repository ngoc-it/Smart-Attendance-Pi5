#!/bin/bash

# Script thiet lap ung dung SmartAttendance chay tu dong nhu mot Dich vu he thong (System Service)
# Thuc hien boi Antigravity AI

APP_DIR="/home/nkn0901/SmartAttendance"
PYTHON_BIN="$APP_DIR/env/bin/python"
SERVICE_FILE="/etc/systemd/system/smartattendance.service"

echo "------------------------------------------------"
echo "Dang thiet lap SmartAttendance Service..."
echo "------------------------------------------------"

# 1. Tao file service (Can quyen sudo)
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Smart Attendance Web Application
After=network-online.target
Wants=network-online.target

[Service]
User=nkn0901
WorkingDirectory=$APP_DIR
ExecStart=$PYTHON_BIN run.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 2. Kick hoat dich vu
echo "Dang kick hoat dich vu..."
sudo systemctl daemon-reload
sudo systemctl enable smartattendance.service
sudo systemctl start smartattendance.service

echo "------------------------------------------------"
echo "THANH CONG! Ung dung se tu dong chay moi khi bat may."
echo "Lenh kiem tra trang thai: sudo systemctl status smartattendance"
echo "Lenh xem log: journalctl -u smartattendance -f"
echo "------------------------------------------------"
