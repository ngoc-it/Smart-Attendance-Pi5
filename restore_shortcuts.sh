#!/bin/bash

# Script tao 2 phím tat rieng biet de tranh nham lan
# Thuc hien boi Antigravity AI

DESKTOP_DIR="/home/nkn0901/Desktop"
APP_DIR="/home/nkn0901/SmartAttendance"

# 1. Tao phím tat CHAY SERVER (Hinh banh rang)
SHORTCUT_RUN="$DESKTOP_DIR/StartServer.desktop"
cat > "$SHORTCUT_RUN" <<EOF
[Desktop Entry]
Name=1. Bật Hệ Thống (Server)
Comment=Chay backend va camera
Exec=lxterminal -e "bash -c 'cd $APP_DIR && ./env/bin/python run.py; exec bash'"
Icon=system-run
Terminal=false
Type=Application
EOF
chmod +x "$SHORTCUT_RUN"

# 2. Tao phím tat MO WEB (Hinh Camera)
SHORTCUT_WEB="$DESKTOP_DIR/OpenWeb.desktop"
cat > "$SHORTCUT_WEB" <<EOF
[Desktop Entry]
Name=2. Vào Quản Lý (Web)
Comment=Mo trinh duyet vao trang diem danh
Exec=chromium-browser --password-store=basic http://localhost:5000
Icon=camera-video
Terminal=false
Type=Application
EOF
chmod +x "$SHORTCUT_WEB"

# Xoa file cu bi trung neu co
rm -f "$DESKTOP_DIR/SmartAttendance.desktop"

echo "------------------------------------------------"
echo "Da khoi phuc va tao moi 2 phím tat rieng biet:"
echo "1. 'Bật Hệ Thống' (De chay code)"
echo "2. 'Vào Quản Lý' (De dang nhap Web)"
echo "------------------------------------------------"
