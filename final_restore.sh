#!/bin/bash

# Script khoi phuc toan bo phím tat voi lenh 'chromium' dung chuan Pi 5
# Thuc hien boi Antigravity AI

DESKTOP_DIR="/home/nkn0901/Desktop"
APP_DIR="/home/nkn0901/SmartAttendance"
CHROME_BIN="/usr/bin/chromium"

# Xoa cac file cu de lam lai tu dau cho sach
rm -f "$DESKTOP_DIR/OpenWeb.desktop"
rm -f "$DESKTOP_DIR/StartServer.desktop"
rm -f "$DESKTOP_DIR/SmartAttendance.desktop"

# 1. PHÍM TẮT CHẠY SERVER (Hinh banh rang)
cat > "$DESKTOP_DIR/1_Chay_He_Thong.desktop" <<EOF
[Desktop Entry]
Name=1. Bật Hệ Thống
Comment=Chay backend va camera
Exec=lxterminal -e "bash -c 'cd $APP_DIR && ./env/bin/python run.py; exec bash'"
Icon=system-run
Terminal=false
Type=Application
EOF

# 2. PHÍM TẮT KIOSK (Hinh Camera - Cai icon cu cua ban)
cat > "$DESKTOP_DIR/2_Man_Hinh_Kiosk.desktop" <<EOF
[Desktop Entry]
Name=2. Màn Hình Kiosk
Comment=Mo giao dien diem danh full man hinh
Exec=$CHROME_BIN --kiosk --app=http://localhost:5000/kiosk
Icon=camera-video
Terminal=false
Type=Application
EOF

# 3. PHÍM TẮT QUẢN LÝ (Hinh Web/Tra cuu)
cat > "$DESKTOP_DIR/3_Trang_Quan_Ly.desktop" <<EOF
[Desktop Entry]
Name=3. Trang Quản Lý
Comment=Mo trang web quan ly diem danh
Exec=$CHROME_BIN http://localhost:5000
Icon=applications-internet
Terminal=false
Type=Application
EOF

# Cap quyen thuc thi cho tat ca
chmod +x $DESKTOP_DIR/*.desktop

echo "------------------------------------------------"
echo "DA KHOI PHUC THANH CONG!"
echo "1. '1. Bật Hệ Thống' - Bam vao day truoc."
echo "2. '2. Màn Hình Kiosk' - Cai icon cu cua ban da quay lai."
echo "3. '3. Trang Quản Lý' - De dang nhap admin."
echo "------------------------------------------------"
