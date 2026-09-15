#!/bin/bash

# Launch script for Smart Attendance Kiosk
# Author: Antigravity

# Path to the project
PROJECT_DIR="/home/nkn0901/SmartAttendance"
cd "$PROJECT_DIR"

# 1. Start the server if not already running
if ! pgrep -f "python run.py" > /dev/null
then
    echo "SmartAttendance: Server is starting..."
    ./env/bin/python run.py > logs/server.log 2>&1 &
    # Wait for the server to be ready
    sleep 8
else
    echo "SmartAttendance: Server is already running."
fi

# 2. Launch Chromium in Kiosk mode
# --kiosk: Fullscreen mode
# --incognito: Don't save cookies/cache (good for kiosks)
# --disable-infobars: Hide the "Chrome is being controlled" bar
# --noerrdialogs: Hide crash dialogs
echo "SmartAttendance: Launching Kiosk UI..."
/usr/bin/chromium --kiosk --password-store=basic --incognito --disable-infobars --noerrdialogs --disable-session-crashed-bubble http://127.0.0.1:5000/kiosk
