#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
#  Central Routing Manager — One-shot installer
#  Run this script once on a fresh Ubuntu 22.04/24.04 VPS:
#      sudo bash install.sh
#
#  After installation, type `l2tp` anywhere to open the CLI manager.
# ────────────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$INSTALL_DIR/venv"
WRAPPER_PATH="/usr/local/bin/l2tp"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERR]${NC}   $*"; }

# ── 0. Root check ────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (sudo bash install.sh)."
    exit 1
fi

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Central Routing Manager — Installer             ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── 0.5. Server Environment Check ────────────────────────────────────
echo -e "${CYAN}Where are you installing this server?${NC}"
echo "1) Public VPS (Direct Internet IP - Recommended)"
echo "2) Local Machine (Behind NAT / Home Modem)"
read -p "Select [1 or 2, default 1]: " SERVER_TYPE
SERVER_TYPE=${SERVER_TYPE:-1}
echo ""

# ── 1. System packages ──────────────────────────────────────────────
info "Installing system packages (strongswan xl2tpd nginx ufw python3-venv)..."
apt-get update -qq
apt-get install -y -qq strongswan xl2tpd nginx ufw python3 python3-venv python3-pip > /dev/null 2>&1
ok "System packages installed."

# ── 2. Python venv ───────────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created at $VENV_DIR"
else
    ok "Virtual environment already exists."
fi

info "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
ok "Python dependencies installed."

# ── 3. .env file ─────────────────────────────────────────────────────
ENV_FILE="$INSTALL_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    info "Generating .env file with random secrets..."
    SECRET_KEY=$("$VENV_DIR/bin/python3" -c "import secrets; print(secrets.token_urlsafe(48))")
    ENCRYPTION_KEY=$("$VENV_DIR/bin/python3" -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    cat > "$ENV_FILE" <<EOF
PANEL_DEV_MODE=0
PANEL_SECRET_KEY=$SECRET_KEY
PANEL_ENCRYPTION_KEY=$ENCRYPTION_KEY
EOF
    chmod 600 "$ENV_FILE"
    ok ".env file created (production mode, unique secrets)."
else
    warn ".env file already exists — skipping."
fi

# ── 4. Create first admin user (if none exists) ─────────────────────
info "Checking for existing admin users..."
HAS_ADMIN=$("$VENV_DIR/bin/python3" -c "
import sys, os
sys.path.insert(0, '$INSTALL_DIR')
os.chdir('$INSTALL_DIR')
# Load env
from pathlib import Path
for line in Path('$ENV_FILE').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()
from app.database import SessionLocal, Base, engine
from app.models import User, UserRole
Base.metadata.create_all(bind=engine)
db = SessionLocal()
count = db.query(User).filter(User.role == UserRole.admin).count()
db.close()
print(count)
" 2>/dev/null || echo "0")

if [[ "$HAS_ADMIN" == "0" ]]; then
    warn "No admin users found. Let's create one now."
    cd "$INSTALL_DIR"
    # Source .env so config picks it up
    set -a; source "$ENV_FILE"; set +a
    "$VENV_DIR/bin/python3" create_admin.py
else
    ok "Admin user(s) already exist ($HAS_ADMIN found)."
fi

# ── 5. Firewall (ufw) ───────────────────────────────────────────────
info "Configuring firewall rules..."
ufw allow 22/tcp   > /dev/null 2>&1 || true   # SSH
ufw allow 80/tcp   > /dev/null 2>&1 || true   # HTTP
ufw allow 443/tcp  > /dev/null 2>&1 || true   # HTTPS
ufw allow 500/udp  > /dev/null 2>&1 || true   # IKE
ufw allow 4500/udp > /dev/null 2>&1 || true   # NAT-T
ufw allow 1701/udp > /dev/null 2>&1 || true   # L2TP
ufw allow 8000/tcp > /dev/null 2>&1 || true   # Panel default port
ufw --force enable  > /dev/null 2>&1 || true
ok "Firewall configured."

# ── 6. systemd service ──────────────────────────────────────────────
info "Installing systemd service..."
cd "$INSTALL_DIR"
set -a; source "$ENV_FILE"; set +a
"$VENV_DIR/bin/python3" -c "
import sys, os
sys.path.insert(0, '$INSTALL_DIR')
os.chdir('$INSTALL_DIR')
from app.services.systemd_manager import install_service, enable_service
install_service()
enable_service()
" 2>/dev/null || warn "Could not install systemd service (running in dev mode?)."
ok "Panel service installed and enabled."

# ── 7. Cron backup ──────────────────────────────────────────────────
info "Enabling nightly auto-backup..."
"$VENV_DIR/bin/python3" -c "
import sys, os
sys.path.insert(0, '$INSTALL_DIR')
os.chdir('$INSTALL_DIR')
from app.services.cron_manager import enable_cron_backup
enable_cron_backup()
" 2>/dev/null || warn "Could not enable cron backup."
ok "Nightly auto-backup enabled."

# ── 8. Register `l2tp` command ───────────────────────────────────────
info "Registering 'l2tp' command..."
cat > "$WRAPPER_PATH" <<EOF
#!/usr/bin/env bash
if [[ \$EUID -ne 0 ]]; then
    exec sudo bash "\$0" "\$@"
fi
cd "$INSTALL_DIR" && set -a && source "$ENV_FILE" 2>/dev/null; set +a && exec "$VENV_DIR/bin/python3" cli.py "\$@"
EOF
chmod +x "$WRAPPER_PATH"
ok "'l2tp' command registered at $WRAPPER_PATH"

# ── Done ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Installation complete!                           ║${NC}"
echo -e "${GREEN}║  Type 'l2tp' to open the management CLI.         ║${NC}"
if [[ "$SERVER_TYPE" == "1" ]]; then
    echo -e "${GREEN}║  Web Panel: http://\$(hostname -I | awk '{print \$1}'):8000/login ║${NC}"
else
    echo -e "${GREEN}║  Local Web Panel: http://\$(hostname -I | awk '{print \$1}'):8000/login ║${NC}"
fi
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

if [[ "$SERVER_TYPE" == "2" ]]; then
    echo -e "${YELLOW}================================================================${NC}"
    echo -e "${YELLOW}⚠️  NAT / LOCAL NETWORK WARNING                                  ${NC}"
    echo -e "${YELLOW}================================================================${NC}"
    echo "You have installed this on a Local Machine."
    echo "The IPsec VPN (for nodes to connect to this Hub) will NOT work over the"
    echo "internet unless you configure Port Forwarding on your modem/router for:"
    echo "   -> UDP Port 500   (IKE)"
    echo "   -> UDP Port 4500  (NAT-T)"
    echo "   -> TCP Port 8000  (Web Panel - optional)"
    echo ""
    read -p "Do you want to install Cloudflare Tunnel to easily expose the Web Panel to the internet without modem config? (y/N): " SETUP_CF
    if [[ "$SETUP_CF" =~ ^[Yy]$ ]]; then
        info "Installing cloudflared..."
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        dpkg -i cloudflared-linux-amd64.deb >/dev/null 2>&1 || true
        rm -f cloudflared-linux-amd64.deb
        ok "cloudflared installed."
        echo ""
        echo -e "${GREEN}To securely access your web panel from ANYWHERE in the world, just run:${NC}"
        echo -e "${CYAN}cloudflared tunnel --url http://127.0.0.1:8000${NC}"
        echo ""
    fi
fi

