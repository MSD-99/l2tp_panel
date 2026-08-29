import time
import shutil

# Cache CPU state for calculation
_last_cpu_time = None

def get_cpu_usage() -> float:
    global _last_cpu_time
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
        parts = [float(x) for x in line.split()[1:]]
        idle = parts[3]
        total = sum(parts)
        
        if _last_cpu_time is None:
            _last_cpu_time = (idle, total)
            time.sleep(0.1)
            with open('/proc/stat', 'r') as f:
                line = f.readline()
            parts = [float(x) for x in line.split()[1:]]
            idle = parts[3]
            total = sum(parts)

        last_idle, last_total = _last_cpu_time
        _last_cpu_time = (idle, total)
        
        idle_diff = idle - last_idle
        total_diff = total - last_total
        
        if total_diff == 0:
            return 0.0
        return round(100.0 * (1.0 - idle_diff / total_diff), 1)
    except Exception:
        return 0.0

def get_ram_usage() -> float:
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        mem_total = 0
        mem_available = 0
        for line in lines:
            if line.startswith('MemTotal:'):
                mem_total = int(line.split()[1])
            elif line.startswith('MemAvailable:'):
                mem_available = int(line.split()[1])
        if mem_total == 0:
            return 0.0
        mem_used = mem_total - mem_available
        return round(100.0 * (mem_used / mem_total), 1)
    except Exception:
        return 0.0

def get_disk_usage() -> float:
    try:
        usage = shutil.disk_usage('/')
        return round(100.0 * (usage.used / usage.total), 1)
    except Exception:
        return 0.0

def get_system_metrics() -> dict:
    return {
        "cpu": get_cpu_usage(),
        "ram": get_ram_usage(),
        "disk": get_disk_usage(),
    }
