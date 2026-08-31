from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.i18n import translate
from app.models import Node, User
from app.schemas import NodeCreate
from app.security import get_web_user, require_admin_web
from app.services import secrets_manager
from app.services.orchestrator import rebuild_all
from app.templates_env import templates

router = APIRouter(prefix="/nodes", tags=["nodes"])


def _lang(request: Request) -> str:
    return getattr(request.state, "lang", "fa")


@router.get("", response_class=HTMLResponse)
def list_nodes(request: Request, db: Session = Depends(get_db), user: User = Depends(get_web_user)):
    nodes = db.query(Node).order_by(Node.id).all()
    return templates.TemplateResponse(
        "nodes_list.html",
        {"request": request, "user": user, "active": "nodes", "nodes": nodes, "new_credentials": None},
    )


@router.get("/new", response_class=HTMLResponse)
def new_node_form(request: Request, user: User = Depends(require_admin_web)):
    return templates.TemplateResponse(
        "node_form.html",
        {"request": request, "user": user, "active": "nodes", "node": None, "errors": []},
    )


@router.post("/new")
def create_node(
    request: Request,
    label: str = Form(...),
    public_ip: str = Form(""),
    subnet_cidr: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_web),
):
    lang = _lang(request)
    try:
        data = NodeCreate(label=label, public_ip=public_ip, subnet_cidr=subnet_cidr)
    except ValidationError as e:
        errors = [err["msg"] for err in e.errors()]
        return templates.TemplateResponse(
            "node_form.html",
            {"request": request, "user": user, "active": "nodes", "node": None, "errors": errors},
            status_code=422,
        )

    if db.query(Node).filter(Node.label == data.label).first():
        errors = [translate("err_label_taken", lang).format(value=data.label)]
        return templates.TemplateResponse(
            "node_form.html",
            {"request": request, "user": user, "active": "nodes", "node": None, "errors": errors},
            status_code=422,
        )
    from app.services.network_utils import allocate_tunnel_ip
    allocated_tunnel_ip = allocate_tunnel_ip(db)

    node = Node(label=data.label, public_ip=data.public_ip, tunnel_ip=allocated_tunnel_ip, subnet_cidr=data.subnet_cidr)
    psk_plain, ppp_plain = secrets_manager.issue_node_credentials(node)
    db.add(node)
    db.commit()
    db.refresh(node)

    rebuild_all(db)

    nodes = db.query(Node).order_by(Node.id).all()
    return templates.TemplateResponse(
        "nodes_list.html",
        {
            "request": request, "user": user, "active": "nodes", "nodes": nodes,
            "new_credentials": {"label": node.label, "psk": psk_plain, "ppp_password": ppp_plain},
        },
    )


@router.get("/{node_id}/edit", response_class=HTMLResponse)
def edit_node_form(node_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin_web)):
    node = db.query(Node).get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=translate("err_node_not_found", _lang(request)))
    return templates.TemplateResponse(
        "node_form.html",
        {"request": request, "user": user, "active": "nodes", "node": node, "errors": []},
    )


@router.post("/{node_id}/edit")
def update_node(
    node_id: int,
    request: Request,
    label: str = Form(...),
    public_ip: str = Form(""),
    subnet_cidr: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_web),
):
    lang = _lang(request)
    node = db.query(Node).get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=translate("err_node_not_found", lang))

    try:
        data = NodeCreate(label=label, public_ip=public_ip, subnet_cidr=subnet_cidr)
    except ValidationError as e:
        errors = [err["msg"] for err in e.errors()]
        return templates.TemplateResponse(
            "node_form.html",
            {"request": request, "user": user, "active": "nodes", "node": node, "errors": errors},
            status_code=422,
        )

    if db.query(Node).filter(Node.label == data.label, Node.id != node_id).first():
        errors = [translate("err_label_taken", lang).format(value=data.label)]
        return templates.TemplateResponse(
            "node_form.html",
            {"request": request, "user": user, "active": "nodes", "node": node, "errors": errors},
            status_code=422,
        )

    node.label = data.label
    node.public_ip = data.public_ip
    node.subnet_cidr = data.subnet_cidr or ""
    db.commit()
    rebuild_all(db)

    return RedirectResponse(url="/nodes", status_code=303)


@router.post("/{node_id}/rotate-secrets")
def rotate_secrets(node_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin_web)):
    node = db.query(Node).get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=translate("err_node_not_found", _lang(request)))

    psk_plain, ppp_plain = secrets_manager.issue_node_credentials(node)
    db.commit()
    rebuild_all(db)

    nodes = db.query(Node).order_by(Node.id).all()
    return templates.TemplateResponse(
        "nodes_list.html",
        {
            "request": request, "user": user, "active": "nodes", "nodes": nodes,
            "new_credentials": {"label": node.label, "psk": psk_plain, "ppp_password": ppp_plain},
        },
    )


@router.post("/{node_id}/delete")
def delete_node(node_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin_web)):
    node = db.query(Node).get(node_id)
    if node:
        db.delete(node)  # dependent connections are removed via cascade in models.py
        db.commit()
        rebuild_all(db)
    return RedirectResponse(url="/nodes", status_code=303)


@router.get("/{node_id}/setup-script", response_class=HTMLResponse)
def setup_script_page(node_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin_web)):
    from app.crypto_utils import decrypt_str
    node = db.query(Node).get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=translate("err_node_not_found", _lang(request)))

    if not node.encrypted_psk or not node.encrypted_ppp_password:
        raise HTTPException(status_code=400, detail="Node credentials not found. Rotate secrets first.")

    psk = decrypt_str(node.encrypted_psk)
    ppp_password = decrypt_str(node.encrypted_ppp_password)

    # Detect central server IP from the request
    host = request.headers.get("host", "").split(":")[0]
    central_ip = host if host else "CENTRAL_SERVER_IP"

    script = _generate_setup_script(
        central_ip=central_ip,
        node_id=node.id,
        node_label=node.label,
        psk=psk,
        ppp_password=ppp_password,
    )
    uninstall_script = _generate_uninstall_script(node.label)
    mikrotik_script = _generate_mikrotik_script(
        central_ip=central_ip,
        node_label=node.label,
        psk=psk,
        ppp_password=ppp_password,
    )

    return templates.TemplateResponse(
        "node_setup_script.html",
        {"request": request, "user": user, "active": "nodes", "node": node, "script": script, "uninstall_script": uninstall_script, "mikrotik_script": mikrotik_script},
    )


def _generate_setup_script(central_ip: str, node_id: int, node_label: str, psk: str, ppp_password: str) -> str:
    return f'''#!/bin/bash
# ============================================================
#  Auto-generated setup script for node: {node_label}
#  Central server: {central_ip}
#  Run this on the NODE server (not the central server!)
#  Usage:  sudo bash setup_{node_label}.sh
# ============================================================
set -e

echo "============================================"
echo "  Node Setup: {node_label}"
echo "  Central Server: {central_ip}"
echo "============================================"

# --- 1. Install required packages ---
echo "[1/6] Installing strongswan and xl2tpd..."
apt-get update -qq
apt-get install -y -qq strongswan xl2tpd > /dev/null 2>&1
echo "  ✓ Packages installed"

# --- 2. Configure IPsec ---
echo "[2/6] Configuring IPsec (strongSwan)..."
cat > /etc/ipsec.conf << 'IPSEC_CONF'
config setup

conn %default
    ikelifetime=24h
    keylife=8h
    rekeymargin=3m
    keyingtries=%forever
    keyexchange=ikev2
    authby=secret
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256!

conn myvpn
    keyexchange=ikev2
    left=%defaultroute
    leftid=@{node_label}
    auto=add
    authby=secret
    type=transport
    leftprotoport=17/%any
    rightprotoport=17/1701
    right={central_ip}
    forceencaps=yes
    dpdaction=restart
    closeaction=restart
    dpddelay=30s
    dpdtimeout=120s
IPSEC_CONF

cat > /etc/ipsec.secrets << IPSEC_SECRETS
%any {central_ip} : PSK "{psk}"
IPSEC_SECRETS
chmod 600 /etc/ipsec.secrets
echo "  ✓ IPsec configured"

# --- 3. Configure xl2tpd ---
echo "[3/6] Configuring xl2tpd..."
cat > /etc/xl2tpd/xl2tpd.conf << 'XL2TPD_CONF'
[lac myvpn]
lns = {central_ip}
ppp debug = yes
pppoptfile = /etc/ppp/options.l2tpd.client
length bit = yes
autodial = yes
redial = yes
redial timeout = 10
XL2TPD_CONF
echo "  ✓ xl2tpd configured"

# --- 4. Configure PPP ---
echo "[4/6] Configuring PPP authentication..."
cat > /etc/ppp/options.l2tpd.client << PPP_OPTIONS
ipcp-accept-local
ipcp-accept-remote
refuse-eap
require-chap
noccp
noauth
mtu 1400
mru 1400
noipdefault
nodefaultroute
usepeerdns
connect-delay 5000
name "{node_label}"
password "{ppp_password}"
PPP_OPTIONS
echo "  ✓ PPP configured"

# --- 4.5. Configure Dynamic Routing ---
echo "[4.5/6] Configuring dynamic VPN routing script..."
cat > /usr/local/bin/l2tp-route-sync.sh << 'SYNC_SCRIPT'
#!/bin/bash
# Fetch routes from Central Server API and apply them
# Usage: /usr/local/bin/l2tp-route-sync.sh

CENTRAL_URL="http://{central_ip}:8000/api/v1/routes/{node_id}"
DESIRED_ROUTES=$(curl -s -H "Authorization: Bearer {psk}" "$CENTRAL_URL")

if [ -z "$DESIRED_ROUTES" ] || [[ "$DESIRED_ROUTES" == *"detail"* ]]; then
    DESIRED_ROUTES=""
fi

# We only care about ppp0 routes (excluding the central IP link route which is a single IP /32)
CURRENT_ROUTES=$(ip route show dev ppp0 2>/dev/null | grep -v 'scope link' | awk '{{print $1}}')

# Add missing routes
for route in $DESIRED_ROUTES; do
    if ! echo "$CURRENT_ROUTES" | grep -q "^$route$"; then
        ip route add "$route" dev ppp0 2>/dev/null || true
    fi
done

# Remove old routes
for route in $CURRENT_ROUTES; do
    if ! echo "$DESIRED_ROUTES" | grep -q "^$route$"; then
        ip route del "$route" dev ppp0 2>/dev/null || true
    fi
done
SYNC_SCRIPT
chmod +x /usr/local/bin/l2tp-route-sync.sh

cat > /etc/ppp/ip-up.d/l2tp-routing << 'IPUP'
#!/bin/bash
if [ "$1" = "ppp0" ]; then
    /usr/local/bin/l2tp-route-sync.sh &
fi
IPUP
chmod +x /etc/ppp/ip-up.d/l2tp-routing

# Setup Cronjob to run every minute
echo "* * * * * root /usr/local/bin/l2tp-route-sync.sh >/dev/null 2>&1" > /etc/cron.d/l2tp-route-sync
chmod 644 /etc/cron.d/l2tp-route-sync
echo "  ✓ Dynamic routing configured"

# --- 5. Restart services and establish tunnel ---
echo "[5/6] Restarting services..."
systemctl restart strongswan-starter 2>/dev/null || true
systemctl restart strongswan 2>/dev/null || true
ipsec restart 2>/dev/null || true
ipsec update 2>/dev/null || true
ipsec rereadsecrets 2>/dev/null || true
sleep 2
ipsec up myvpn 2>/dev/null || true

systemctl restart xl2tpd
sleep 2
mkdir -p /var/run/xl2tpd
echo "c myvpn" > /var/run/xl2tpd/l2tp-control
echo "  ✓ Services restarted"

# --- 6. Wait for tunnel and verify ---
echo "[6/6] Waiting for tunnel interface (ppp0)..."
sleep 5
if ip addr show ppp0 > /dev/null 2>&1; then
    TUNNEL_IP=$(ip -4 addr show ppp0 | grep -oP "(?<=inet )\\S+" | cut -d/ -f1)
    echo ""
    echo "============================================"
    echo "  ✅ SUCCESS! Tunnel is UP"
    echo "  Tunnel IP: $TUNNEL_IP"
    echo "  Node: {node_label}"
    echo "============================================"
else
    echo ""
    echo "============================================"
    echo "  ⚠ Tunnel interface ppp0 not found yet."
    echo "  Check logs: tail -n 30 /var/log/syslog"
    echo "============================================"
    echo "============================================"
fi
'''

def _generate_uninstall_script(node_label: str) -> str:
    return f'''#!/bin/bash
# ============================================================
#  Uninstall script for node: {node_label}
#  Run this on the NODE server to completely remove the VPN
# ============================================================
set -e

echo "Stopping services..."
systemctl stop xl2tpd 2>/dev/null || true
ipsec down myvpn 2>/dev/null || true
ipsec stop 2>/dev/null || true
systemctl stop strongswan-starter 2>/dev/null || true

echo "Removing configuration files..."
rm -f /etc/ipsec.conf /etc/ipsec.secrets
rm -f /etc/xl2tpd/xl2tpd.conf
rm -f /etc/ppp/options.l2tpd.client
rm -f /etc/ppp/ip-up.d/l2tp-routing
rm -f /usr/local/bin/l2tp-route-sync.sh
rm -f /etc/cron.d/l2tp-route-sync

echo "Disabling services..."
systemctl disable xl2tpd 2>/dev/null || true
systemctl disable strongswan-starter 2>/dev/null || true

echo "============================================"
echo "  ✅ Node {node_label} has been successfully uninstalled."
echo "============================================"
'''


def _generate_mikrotik_script(central_ip: str, node_label: str, psk: str, ppp_password: str) -> str:
    return f'''# ============================================================
#  MikroTik RouterOS Setup Script for node: {node_label}
#  Central server: {central_ip}
#  Run this in the MikroTik Terminal
# ============================================================

/ppp profile
add name=l2tp_hub_profile use-encryption=yes use-mpls=default use-upnp=no

/interface l2tp-client
add allow=mschap2 connect-to={central_ip} disabled=no \\
    ipsec-secret="{psk}" name="l2tp_hub" password="{ppp_password}" \\
    profile=l2tp_hub_profile use-ipsec=yes user="{node_label}"

# Add a default route to the VPN (Optional - remove if not needed)
# /ip route add dst-address=10.10.10.0/24 gateway=l2tp_hub
'''
