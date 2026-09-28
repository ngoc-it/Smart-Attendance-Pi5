import os
import subprocess

def get_cpu_temperature():
    """Lấy nhiệt độ CPU của Raspberry Pi (hoặc Linux hệ thống). Trả về float (°C) hoặc None."""
    thermal_file = "/sys/class/thermal/thermal_zone0/temp"
    if os.path.exists(thermal_file):
        try:
            with open(thermal_file, "r") as f:
                temp_mc = int(f.read().strip())
                return round(temp_mc / 1000.0, 1)
        except Exception:
            pass

    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"], timeout=2).decode("utf-8")
        if "temp=" in out:
            return float(out.replace("temp=", "").replace("'C", "").strip())
    except Exception:
        pass

    return None

def get_ram_usage():
    """Lấy thông tin dung lượng RAM đang sử dụng của hệ thống."""
    try:
        mem_info = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    mem_info[parts[0].strip()] = int(parts[1].split()[0].strip())
        
        total_kb = mem_info.get("MemTotal", 0)
        avail_kb = mem_info.get("MemAvailable", mem_info.get("MemFree", 0))
        used_kb = total_kb - avail_kb
        
        if total_kb > 0:
            percent = round((used_kb / total_kb) * 100, 1)
            used_gb = round(used_kb / (1024 * 1024), 2)
            total_gb = round(total_kb / (1024 * 1024), 2)
            
            status = "normal"
            status_text = "Bình thường"
            color = "#38a169" # green
            if percent >= 85.0:
                status = "critical"
                status_text = "Cảnh báo RAM sắp cạn!"
                color = "#e53e3e" # red
            elif percent >= 70.0:
                status = "warning"
                status_text = "Cảnh báo RAM khá cao"
                color = "#d69e2e" # yellow/orange

            return {
                "percent": percent,
                "used_gb": used_gb,
                "total_gb": total_gb,
                "text": f"{used_gb}/{total_gb} GB ({percent}%)",
                "status": status,
                "status_text": status_text,
                "color": color
            }
    except Exception:
        pass
    return None

def get_system_stats():
    """Trả về dict chứa thông tin giám sát phần cứng Raspberry Pi (CPU Temp & RAM)."""
    temp = get_cpu_temperature()
    status = "normal"
    status_text = "Bình thường"
    color = "#38a169" # Xanh lá (Hoạt động tốt)

    if temp is not None:
        if temp >= 75.0:
            status = "critical"
            status_text = "Cảnh báo Quá nhiệt!"
            color = "#e53e3e" # Đỏ (Nóng nguy hiểm)
        elif temp >= 65.0:
            status = "warning"
            status_text = "Cảnh báo Ấm"
            color = "#d69e2e" # Vàng (Khá nóng)

    return {
        "cpu_temp": temp,
        "temp_status": status,
        "temp_status_text": status_text,
        "temp_color": color,
        "ram": get_ram_usage()
    }
