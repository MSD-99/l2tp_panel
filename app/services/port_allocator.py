import subprocess

from sqlalchemy.orm import Session

from app.config import DEV_MODE
from app.models import Connection

PORT_RANGE_START = 8080
PORT_RANGE_END = 65000


def _port_busy_on_os(port: int) -> bool:
    if DEV_MODE:
        # In the dev/test environment there's no real server socket to check
        return False
    try:
        result = subprocess.run(
            ["ss", "-tuln"], capture_output=True, text=True, timeout=3
        )
        return f":{port} " in result.stdout
    except Exception:
        # If ss isn't available, just rely on the database
        return False


def find_free_port(db: Session) -> int:
    used_ports = {p for (p,) in db.query(Connection.port).filter(Connection.port.isnot(None)).all()}
    port = PORT_RANGE_START
    while port < PORT_RANGE_END:
        if port not in used_ports and not _port_busy_on_os(port):
            return port
        port += 1
    raise RuntimeError("No free port found in the allowed range.")
