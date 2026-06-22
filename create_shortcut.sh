#!/bin/bash

# Script tao phím tat (Desktop Shortcut) cho Raspberry Pi
# Thuc hien boi Antigravity AI

DESKTOP_DIR="/home/nkn0901/Desktop"
APP_DIR="/home/nkn0901/SmartAttendance"
ICON_PATH="/usr/share/icons/PiX/48x48/apps/rpi.png" # Icon mac dinh cua Pi, ban co the thay doi sau

# Neu thu muc Desktop khong ton tai (tuy vao cau hinh ngon ngu), thu tim Desktop
if [ ! -d "$DESKTOP_DIR" ]; then
    DESKTOP_DIR="/home/nkn0901/Desktop"
fi

SHORTCUT_FILE="$DESKTOP_DIR/SmartAttendance.desktop"
# Su dung icon camera cua he thong
ICON_PATH="/usr/share/icons/PiX/48x48/apps/camera.png" 

cat > "$SHORTCUT_FILE" <<EOF
[Desktop Entry]
Name=Hệ Thống Điểm Danh
Comment=Mo camera va bat dau diem danh
Exec=lxterminal -e "bash -c 'cd $APP_DIR && ./env/bin/python run.py; exec bash'"
Icon=camera-video
Terminal=false
Type=Application
Categories=Application;Development;
EOF

# Cap quyen thuc thi cho phím tat
chmod +x "$SHORTCUT_FILE"

echo "------------------------------------------------"
echo "Da tao phím tat 'Bat Diem Danh' tren man hinh Desktop!"
echo "Ban chi can ra man hinh chinh va nhap vao no de chay."
echo "------------------------------------------------"
