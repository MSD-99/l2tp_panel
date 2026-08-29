"""
Log manager: provides tail and streaming access to the panel's log output.

In production (PANEL_DEV_MODE=0):
    Reads from journalctl -u central_panel.service

In dev mode (PANEL_DEV_MODE=1):
    Reads from a local log file (BASE_DIR/panel.log)
"""
import asyncio
import subprocess
from pathlib import Path

from app.config import DEV_MODE, PANEL_SERVICE_NAME, LOG_FILE


def tail_lines(n: int = 100) -> list[str]:
    """Return the last *n* log lines (blocking, suitable for CLI)."""
    if DEV_MODE:
        if not LOG_FILE.exists():
            return ["(no log file yet — start the panel first)"]
        lines = LOG_FILE.read_text(errors="replace").splitlines()
        return lines[-n:]
    try:
        result = subprocess.run(
            ["journalctl", "-u", PANEL_SERVICE_NAME, "--no-pager", "-n", str(n)],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.splitlines()
    except Exception as e:
        return [f"(error reading journal: {e})"]


async def stream_lines():
    """Async generator: yields new log lines as they appear (for SSE)."""
    if DEV_MODE:
        # Tail the local log file
        if not LOG_FILE.exists():
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            LOG_FILE.touch()
        proc = await asyncio.create_subprocess_exec(
            "tail", "-f", "-n", "50", str(LOG_FILE),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            "journalctl", "-u", PANEL_SERVICE_NAME, "-f", "--no-pager", "-n", "50",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line.decode(errors="replace").rstrip("\n")
    finally:
        proc.kill()
        await proc.wait()


async def stream_node_lines(node_label: str, tunnel_ip: str):
    """Async generator: yields VPN/System log lines specific to a single node."""
    if DEV_MODE:
        # Just return some dummy data
        yield f"[{node_label}] (Dev Mode) Tail of system logs for IP: {tunnel_ip}"
        await asyncio.sleep(2)
        yield "xl2tpd: connection established"
        return
        
    # We want to tail syslog or journalctl for pppd, xl2tpd, charon and filter
    # by the node's label or IP. 
    # To do this safely, we tail everything and filter in Python.
    proc = await asyncio.create_subprocess_exec(
        "journalctl", "-u", "ipsec", "-u", "xl2tpd", "-f", "--no-pager", "-n", "100",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            decoded = line.decode(errors="replace").rstrip("\n")
            if node_label in decoded or tunnel_ip in decoded:
                yield decoded
    finally:
        proc.kill()
        await proc.wait()


def follow_blocking():
    """Blocking generator for CLI live-log (runs until KeyboardInterrupt)."""
    if DEV_MODE:
        if not LOG_FILE.exists():
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            LOG_FILE.touch()
        cmd = ["tail", "-f", "-n", "50", str(LOG_FILE)]
    else:
        cmd = ["journalctl", "-u", PANEL_SERVICE_NAME, "-f", "--no-pager", "-n", "50"]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        for line in iter(proc.stdout.readline, ""):
            yield line.rstrip("\n")
    finally:
        proc.kill()
        proc.wait()
