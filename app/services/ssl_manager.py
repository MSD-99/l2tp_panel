import re
import shutil
import subprocess

from app.config import DEV_MODE
from app.settings import save_settings

DOMAIN_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$")


def is_valid_domain(domain: str) -> bool:
    domain = domain.strip()
    if not DOMAIN_RE.match(domain):
        return False
    # Reject IP addresses (e.g. "185.97.119.91") - a real TLD is never all-digit
    last_label = domain.rsplit(".", 1)[-1]
    if last_label.isdigit():
        return False
    return True


def certbot_available() -> bool:
    return shutil.which("certbot") is not None


def install_certbot() -> dict:
    if DEV_MODE:
        return {"applied": False, "output": "(dry-run) would run: apt-get install -y certbot python3-certbot-nginx"}
    try:
        result = subprocess.run(
            ["apt-get", "install", "-y", "certbot", "python3-certbot-nginx"],
            capture_output=True, text=True, timeout=300,
        )
        return {"applied": result.returncode == 0, "output": (result.stdout + result.stderr)[-2000:]}
    except Exception as e:
        return {"applied": False, "output": str(e)}


def obtain_certificate(domain: str, email: str | None = None) -> dict:
    """
    Runs certbot's Nginx plugin to obtain + install a certificate for the
    given domain. Requires the domain's DNS A/AAAA record to already point
    at this server - certbot will fail otherwise (that's expected and not
    something this tool can fix).
    """
    if not is_valid_domain(domain):
        return {"applied": False, "output": f"'{domain}' does not look like a valid domain name."}

    if DEV_MODE:
        return {"applied": False, "output": f"(dry-run) would run: certbot --nginx -d {domain} ..."}

    cmd = ["certbot", "--nginx", "-d", domain, "--non-interactive", "--agree-tos"]
    if email:
        cmd += ["-m", email]
    else:
        cmd += ["--register-unsafely-without-email"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        applied = result.returncode == 0
        if applied:
            save_settings({"domain": domain, "ssl_enabled": True})
        return {"applied": applied, "output": (result.stdout + result.stderr)[-3000:]}
    except Exception as e:
        return {"applied": False, "output": str(e)}
