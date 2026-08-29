import subprocess

from app.config import DEV_MODE
from sqlalchemy.orm import Session
import ipaddress

def allocate_tunnel_ip(db: Session) -> str:
    from app.models import Node
    used_ips = {n.tunnel_ip for n in db.query(Node.tunnel_ip).filter(Node.tunnel_ip.isnot(None)).all()}
    base_ip = ipaddress.IPv4Address('10.10.10.2')
    while True:
        ip_str = str(base_ip)
        if ip_str not in used_ips:
            return ip_str
        base_ip += 1

# Ports the panel cares about, per the phase-3 report's own list
KNOWN_PORTS = {
    "http": 80,
    "https": 443,
    "l2tp": 1701,
    "ipsec_ike": 500,
    "ipsec_nat_t": 4500,
}


def ping(ip: str) -> bool:
    if DEV_MODE:
        # In the dev/test environment there's no real tunnel network to reach
        return True
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", ip], capture_output=True, timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False


def port_status(panel_port: int | None = None) -> dict:
    """Returns {port_name: is_listening} for the known ports plus the panel's own."""
    ports = dict(KNOWN_PORTS)
    if panel_port:
        ports["panel"] = panel_port

    if DEV_MODE:
        return {name: None for name in ports}  # None = unknown (not checked in DEV_MODE)

    try:
        result = subprocess.run(["ss", "-tuln"], capture_output=True, text=True, timeout=3)
        listening = result.stdout
    except Exception:
        return {name: None for name in ports}

    return {name: f":{port} " in listening for name, port in ports.items()}
