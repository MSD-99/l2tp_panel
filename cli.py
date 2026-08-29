#!/usr/bin/env python3
"""
Central Routing Manager - CLI

Full-parity terminal admin tool for the panel, sharing the same database
and service layer as the web panel (app/services/*). Anything changed here
is immediately visible in the web panel and vice versa.

Usage:
    python3 cli.py          # or just `l2tp` after install
"""
import getpass
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.theme import Theme

from app.database import SessionLocal, Base, engine
from app.models import Node, Connection, User, UserRole, ConnectionMode
from app.schemas import NodeCreate, ConnectionCreate, UserCreate
from app.security import hash_password
from app.settings import load_settings, save_settings
from app.services import (
    secrets_manager, backup_manager, cron_manager, systemd_manager,
    service_control, ssl_manager, update_manager, uninstall_manager,
    log_manager,
)
from app.services.orchestrator import rebuild_all
from app.services.network_utils import ping, port_status
from app.services.port_allocator import find_free_port
from app.config import DEV_MODE
from pydantic import ValidationError

PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"

theme = Theme({
    "accent": "#45d8c4",
    "warn": "#f2b84b",
    "danger": "#e5534b",
    "muted": "#8b94a7",
})
console = Console(theme=theme)

Base.metadata.create_all(bind=engine)


def banner():
    console.print(Panel(
        "[accent bold]CENTRAL ROUTING MANAGER[/accent bold] · CLI\n"
        "[muted]Shares the same database as the web panel — changes apply to both.[/muted]"
        + ("\n[warn]DEV_MODE is active — write operations are dry-run only.[/warn]" if DEV_MODE else ""),
        border_style="accent",
    ))


def pause():
    Prompt.ask("\n[muted]Press Enter to continue[/muted]", default="", show_default=False)


# ============================== i) Install (Full Setup) ==============================

INSTALL_RESUME_ENV = "PANEL_INSTALL_RESUME"


def menu_install(resumed: bool = False):
    """One-shot installation wizard — mirrors install.sh but runs interactively."""
    console.rule("[accent]Full Setup Wizard[/accent]")

    if not _is_root():
        console.print("[danger]This wizard needs root privileges.[/danger]")
        console.print("[muted]Run as: sudo l2tp  (or sudo python3 cli.py)[/muted]")
        pause()
        return

    if not resumed:
        if not Confirm.ask(
            "[warn]This will install system packages, create configs, and enable services. Continue?[/warn]",
            default=True,
        ):
            return

        early_steps = [
            ("Installing system packages (strongswan, xl2tpd, nginx, ufw)...", _step_system_packages),
            ("Setting up Python virtual environment...", _step_venv),
            ("Installing Python dependencies...", _step_pip),
        ]
        for description, step_fn in early_steps:
            console.print(f"\n[accent]→ {description}[/accent]")
            try:
                result = step_fn()
                if result:
                    console.print(f"  [muted]{result}[/muted]")
                console.print("  [accent]✓ Done[/accent]")
            except Exception as e:
                console.print(f"  [danger]✗ Error: {e}[/danger]")
                if not Confirm.ask("  Continue with remaining steps?", default=True):
                    return

        env_already_existed = ENV_FILE.exists()
        console.print("\n[accent]→ Generating .env secrets...[/accent]")
        try:
            result = _step_env_file()
            console.print(f"  [muted]{result}[/muted]")
            console.print("  [accent]✓ Done[/accent]")
        except Exception as e:
            console.print(f"  [danger]✗ Error: {e}[/danger]")
            pause()
            return

        # If .env was JUST created (not pre-existing), this running process
        # still has DEV_MODE=True frozen in memory - and in every module that
        # already imported it (database.py's engine/SessionLocal, systemd_
        # manager.py, cron_manager.py, ...). No in-process trick fixes this;
        # only a real restart does, so the DB connection itself gets rebuilt
        # against the right path too. We verified this empirically - writing
        # .env or even mutating app.config.DEV_MODE directly does NOT change
        # names other modules already imported via "from app.config import
        # DEV_MODE". Without this restart, the remaining steps would silently
        # create the admin user in the wrong (dev) database and no-op the
        # systemd/cron setup while still printing "✓ Done".
        if not env_already_existed:
            console.print(
                "\n[warn]Restarting to apply the new production settings before "
                "continuing (this process can't hot-reload them)...[/warn]"
            )
            os.environ[INSTALL_RESUME_ENV] = "1"
            os.execv(sys.executable, [sys.executable] + sys.argv)
            return  # unreachable - the process is replaced by the line above

    if resumed:
        console.print("[accent]Resumed after restart — production settings are now active.[/accent]")

    later_steps = [
        ("Creating admin user...", _step_create_admin),
        ("Configuring firewall (ufw)...", _step_firewall),
        ("Installing & enabling panel systemd service...", _step_systemd),
        ("Enabling nightly auto-backup (cron)...", _step_cron),
        ("Registering 'l2tp' system command...", _step_register_command),
    ]
    for description, step_fn in later_steps:
        console.print(f"\n[accent]→ {description}[/accent]")
        try:
            result = step_fn()
            if result:
                console.print(f"  [muted]{result}[/muted]")
            console.print("  [accent]✓ Done[/accent]")
        except Exception as e:
            console.print(f"  [danger]✗ Error: {e}[/danger]")
            if not Confirm.ask("  Continue with remaining steps?", default=True):
                break

    console.print(Panel(
        "[accent bold]Installation complete![/accent bold]\n"
        "[muted]Type 'l2tp' from any terminal to manage the server.[/muted]",
        border_style="accent",
    ))
    pause()


def _is_root() -> bool:
    return os.geteuid() == 0


def _step_system_packages() -> str:
    result = subprocess.run(
        ["apt-get", "install", "-y", "-qq", "strongswan", "xl2tpd", "nginx", "ufw", "python3-venv"],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-500:])
    return "strongswan, xl2tpd, nginx, ufw installed"


def _step_venv() -> str:
    venv_dir = PROJECT_DIR / "venv"
    if venv_dir.exists():
        return "venv already exists"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, timeout=60)
    return f"created at {venv_dir}"


def _step_pip() -> str:
    pip = PROJECT_DIR / "venv" / "bin" / "pip"
    subprocess.run([str(pip), "install", "--upgrade", "pip", "-q"], check=True, timeout=120)
    subprocess.run(
        [str(pip), "install", "-r", str(PROJECT_DIR / "requirements.txt"), "-q"],
        check=True, timeout=300,
    )
    return "all Python packages installed"


def _step_env_file() -> str:
    if ENV_FILE.exists():
        return ".env already exists — skipping"
    # Generate unique secrets
    import secrets as _secrets
    from cryptography.fernet import Fernet
    secret_key = _secrets.token_urlsafe(48)
    encryption_key = Fernet.generate_key().decode()
    ENV_FILE.write_text(
        f"PANEL_DEV_MODE=0\n"
        f"PANEL_SECRET_KEY={secret_key}\n"
        f"PANEL_ENCRYPTION_KEY={encryption_key}\n"
    )
    os.chmod(str(ENV_FILE), 0o600)
    return "generated with unique secrets (production mode)"


def _step_create_admin() -> str:
    db = SessionLocal()
    try:
        count = db.query(User).filter(User.role == UserRole.admin).count()
        if count > 0:
            return f"{count} admin user(s) already exist — skipping"
        console.print("  [warn]No admin users found. Let's create one.[/warn]")
        username = Prompt.ask("  Username")
        password = Prompt.ask("  Password", password=True)
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        user = User(username=username, password_hash=hash_password(password), role=UserRole.admin)
        db.add(user)
        db.commit()
        return f"admin user '{username}' created"
    finally:
        db.close()


def _step_firewall() -> str:
    for rule in ["22/tcp", "80/tcp", "443/tcp", "500/udp", "4500/udp", "1701/udp", "8000/tcp"]:
        subprocess.run(["ufw", "allow", rule], capture_output=True, timeout=10)
    subprocess.run(["ufw", "--force", "enable"], capture_output=True, timeout=10)
    return "ports 22,80,443,500,4500,1701,8000 allowed"


def _step_systemd() -> str:
    systemd_manager.install_service()
    result = systemd_manager.enable_service()
    return f"applied={result.get('applied', False)}"


def _step_cron() -> str:
    result = cron_manager.enable_cron_backup()
    return f"applied={result.get('applied', False)}"


def _step_register_command() -> str:
    wrapper_path = Path("/usr/local/bin/l2tp")
    venv_python = PROJECT_DIR / "venv" / "bin" / "python3"
    wrapper_path.write_text(
        f'#!/usr/bin/env bash\n'
        f'cd "{PROJECT_DIR}" && set -a && source "{ENV_FILE}" 2>/dev/null; '
        f'set +a && exec "{venv_python}" cli.py "$@"\n'
    )
    wrapper_path.chmod(0o755)
    return f"registered at {wrapper_path}"


# ============================== 1) Service Management ==============================

def menu_services():
    while True:
        console.rule("[accent]Service Management[/accent]")
        table = Table(show_header=True, header_style="muted")
        table.add_column("#")
        table.add_column("Service")
        table.add_column("Status")

        services = [
            ("1", "ipsec (strongSwan)", service_control.CORE_SERVICES["ipsec"]),
            ("2", "xl2tpd", service_control.CORE_SERVICES["xl2tpd"]),
            ("3", "nginx", service_control.CORE_SERVICES["nginx"]),
            ("4", "Web Panel", None),  # handled separately via systemd_manager
        ]
        for idx, name, unit in services:
            status = systemd_manager.service_status() if unit is None else service_control.service_status_text(unit)
            color = "accent" if status == "active" else "danger" if status not in ("unknown", "unknown (DEV_MODE)") else "muted"
            table.add_row(idx, name, f"[{color}]{status}[/{color}]")
        console.print(table)

        console.print("\n[muted]a) start  b) stop  c) restart  0) back[/muted]")
        action = Prompt.ask("Action", choices=["a", "b", "c", "0"], default="0")
        if action == "0":
            return

        svc_choice = Prompt.ask("Which service (1-4)", choices=["1", "2", "3", "4"])
        action_name = {"a": "start", "b": "stop", "c": "restart"}[action]

        if svc_choice == "4":
            result = {"start": systemd_manager.start_service, "stop": systemd_manager.stop_service,
                      "restart": systemd_manager.restart_service}[action_name]()
        else:
            unit = dict(zip(["1", "2", "3"], service_control.CORE_SERVICES.values()))[svc_choice]
            result = service_control.service_action(unit, action_name)

        console.print(f"[muted]{result}[/muted]")
        pause()


# ============================== 2) Recovery & Security ==============================

def menu_recovery(db):
    while True:
        console.rule("[accent]Recovery & Security[/accent]")
        console.print(
            "1) Reset admin password\n"
            "2) Change web panel port\n"
            "3) Change login path\n"
            "0) Back"
        )
        choice = Prompt.ask("Choice", choices=["1", "2", "3", "0"], default="0")
        if choice == "0":
            return

        if choice == "1":
            users = db.query(User).order_by(User.id).all()
            if not users:
                console.print("[danger]No users exist yet.[/danger]")
                pause()
                continue
            table = Table()
            table.add_column("#")
            table.add_column("Username")
            table.add_column("Role")
            for i, u in enumerate(users, 1):
                table.add_row(str(i), u.username, u.role.value)
            console.print(table)
            idx = IntPrompt.ask("Select user #", default=1)
            if not (1 <= idx <= len(users)):
                console.print("[danger]Invalid selection.[/danger]")
                pause()
                continue
            target = users[idx - 1]
            new_password = Prompt.ask("New password", password=True)
            if len(new_password) < 8:
                console.print("[danger]Password must be at least 8 characters.[/danger]")
                pause()
                continue
            target.password_hash = hash_password(new_password)
            db.commit()
            console.print(f"[accent]Password for '{target.username}' updated.[/accent]")
            pause()

        elif choice == "2":
            current = load_settings()["panel_port"]
            new_port = IntPrompt.ask(f"New panel port (current: {current})", default=current)
            if not (1 <= new_port <= 65535):
                console.print("[danger]Port must be between 1 and 65535.[/danger]")
                pause()
                continue
            save_settings({"panel_port": new_port})
            console.print(f"[accent]Panel port set to {new_port}.[/accent] "
                          "[warn]Restart the panel service for this to take effect.[/warn]")
            if Confirm.ask("Restart the panel service now?", default=False):
                console.print(systemd_manager.restart_service())
            pause()

        elif choice == "3":
            current = load_settings()["login_path"]
            new_path = Prompt.ask(f"New login path (current: {current})", default=current)
            if not new_path.startswith("/"):
                new_path = "/" + new_path
            save_settings({"login_path": new_path})
            console.print(f"[accent]Login path set to {new_path}.[/accent] "
                          "[warn]Restart the panel service for this to take effect.[/warn]")
            if Confirm.ask("Restart the panel service now?", default=False):
                console.print(systemd_manager.restart_service())
            pause()


# ============================== 3) Network & Server ==============================

def menu_network(db):
    while True:
        console.rule("[accent]Network & Server[/accent]")
        console.print(
            "1) Port status\n"
            "2) Connectivity test (ping registered nodes)\n"
            "3) SSL / domain setup\n"
            "0) Back"
        )
        choice = Prompt.ask("Choice", choices=["1", "2", "3", "0"], default="0")
        if choice == "0":
            return

        if choice == "1":
            settings = load_settings()
            statuses = port_status(panel_port=settings["panel_port"])
            table = Table()
            table.add_column("Port")
            table.add_column("Listening")
            for name, is_listening in statuses.items():
                if is_listening is None:
                    text = "[muted]unknown (DEV_MODE)[/muted]"
                elif is_listening:
                    text = "[accent]yes[/accent]"
                else:
                    text = "[danger]no[/danger]"
                table.add_row(name, text)
            console.print(table)
            pause()

        elif choice == "2":
            nodes = db.query(Node).order_by(Node.id).all()
            if not nodes:
                console.print("[muted]No nodes registered yet.[/muted]")
                pause()
                continue
            table = Table()
            table.add_column("Node")
            table.add_column("Tunnel IP")
            table.add_column("Reachable")
            for n in nodes:
                ok = ping(n.tunnel_ip)
                text = "[accent]yes[/accent]" if ok else "[danger]no[/danger]"
                table.add_row(n.label, n.tunnel_ip, text)
            console.print(table)
            pause()

        elif choice == "3":
            console.print(
                "[muted]Real SSL (Let's Encrypt) requires a domain that already "
                "points its DNS A/AAAA record at this server's public IP — a raw "
                "IP address cannot get a certificate.[/muted]"
            )
            domain = Prompt.ask("Domain (e.g. panel.example.com)")
            if not ssl_manager.is_valid_domain(domain):
                console.print("[danger]That doesn't look like a valid domain.[/danger]")
                pause()
                continue
            if not ssl_manager.certbot_available():
                if Confirm.ask("certbot is not installed. Install it now?", default=True):
                    console.print(ssl_manager.install_certbot())
            email = Prompt.ask("Email for renewal notices (optional)", default="")
            result = ssl_manager.obtain_certificate(domain, email or None)
            console.print(result)
            pause()


# ============================== 4) Backup & Restore ==============================

def menu_backup():
    while True:
        console.rule("[accent]Backup & Restore[/accent]")
        backups = backup_manager.list_backups()
        table = Table()
        table.add_column("#")
        table.add_column("Filename")
        table.add_column("Size")
        table.add_column("Modified")
        for i, b in enumerate(backups, 1):
            table.add_row(str(i), b["filename"], f"{b['size_kb']} KB", b["modified"])
        console.print(table if backups else "[muted]No backups yet.[/muted]")

        cron_enabled = cron_manager.cron_status()
        console.print(f"\nNightly auto-backup: {'[accent]enabled[/accent]' if cron_enabled else '[muted]disabled[/muted]'}")
        console.print(
            "1) Create backup now\n"
            "2) Restore from a backup\n"
            "3) Toggle nightly auto-backup\n"
            "0) Back"
        )
        choice = Prompt.ask("Choice", choices=["1", "2", "3", "0"], default="0")
        if choice == "0":
            return

        if choice == "1":
            result = backup_manager.create_backup(triggered_by="cli")
            console.print(f"[accent]Backup created: {result['filename']} ({result['size_kb']} KB)[/accent]")
            pause()

        elif choice == "2":
            if not backups:
                console.print("[muted]No backups to restore.[/muted]")
                pause()
                continue
            idx = IntPrompt.ask("Select backup # to restore", default=1)
            if not (1 <= idx <= len(backups)):
                console.print("[danger]Invalid selection.[/danger]")
                pause()
                continue
            filename = backups[idx - 1]["filename"]
            if Confirm.ask(f"[warn]This replaces the current database with '{filename}'. Continue?[/warn]", default=False):
                result = backup_manager.restore_backup(filename)
                console.print(result)
            pause()

        elif choice == "3":
            if cron_enabled:
                console.print(cron_manager.disable_cron_backup())
            else:
                console.print(cron_manager.enable_cron_backup())
            pause()


# ============================== 5) Node Management ==============================

def _get_public_ip() -> str:
    import urllib.request
    try:
        req = urllib.request.Request("https://ident.me", headers={'User-Agent': 'Mozilla/5.0'})
        return urllib.request.urlopen(req, timeout=3).read().decode('utf8').strip()
    except Exception:
        return ""


def _print_nodes_table(nodes):
    table = Table()
    table.add_column("#")
    table.add_column("Label")
    table.add_column("Tunnel IP")
    table.add_column("Subnet")
    table.add_column("Status")
    for i, n in enumerate(nodes, 1):
        ok = ping(n.tunnel_ip)
        status_text = "[accent]online[/accent]" if ok else "[danger]offline[/danger]"
        table.add_row(str(i), n.label, n.tunnel_ip, n.subnet_cidr, status_text)
    console.print(table if nodes else "[muted]No nodes registered yet.[/muted]")


def _save_node_script(node: Node):
    from app.crypto_utils import decrypt_str
    from app.routers.nodes import _generate_setup_script
    psk = decrypt_str(node.encrypted_psk)
    ppp_password = decrypt_str(node.encrypted_ppp_password)
    
    ip = _get_public_ip()
    central_ip = Prompt.ask("Central Server Public IP", default=ip)
    
    script = _generate_setup_script(central_ip, node.id, node.label, psk, ppp_password)
    filename = f"setup_{node.label}.sh"
    with open(filename, "w") as f:
        f.write(script)
    console.print(f"[accent]Setup script saved to {os.path.abspath(filename)}[/accent]")


def _prompt_save_script(node: Node):
    if Confirm.ask(f"Save the auto-configuration script for {node.label} to a file?", default=True):
        _save_node_script(node)


def menu_nodes(db):
    while True:
        console.rule("[accent]Node Management[/accent]")
        nodes = db.query(Node).order_by(Node.id).all()
        _print_nodes_table(nodes)
        console.print(
            "\n1) Add node\n"
            "2) Delete node\n"
            "3) Rotate PSK/PPP secret\n"
            "4) Generate Setup Script\n"
            "0) Back"
        )
        choice = Prompt.ask("Choice", choices=["1", "2", "3", "4", "0"], default="0")
        if choice == "0":
            return

        if choice == "1":
            label = Prompt.ask("Label (e.g. Isfahan)")
            public_ip = Prompt.ask("Public IP (e.g. 188.121.109.115)")
            subnet_cidr = Prompt.ask("LAN subnet CIDR (optional, e.g. 192.168.10.0/24)", default="")
            try:
                data = NodeCreate(label=label, public_ip=public_ip, subnet_cidr=subnet_cidr)
            except ValidationError as e:
                for err in e.errors():
                    console.print(f"[danger]{err['msg']}[/danger]")
                pause()
                continue

            if db.query(Node).filter(Node.label == data.label).first():
                console.print(f"[danger]Label '{data.label}' is already in use.[/danger]")
                pause()
                continue

            from app.services.network_utils import allocate_tunnel_ip
            allocated_tunnel_ip = allocate_tunnel_ip(db)

            node = Node(label=data.label, public_ip=data.public_ip, tunnel_ip=allocated_tunnel_ip, subnet_cidr=data.subnet_cidr or "")
            psk, ppp = secrets_manager.issue_node_credentials(node)
            db.add(node)
            db.commit()
            rebuild_all(db)

            console.print(Panel(
                f"[warn bold]Shown only once — copy these now:[/warn bold]\n"
                f"PSK: [accent]{psk}[/accent]\nPPP Password: [accent]{ppp}[/accent]",
                border_style="warn",
            ))
            _prompt_save_script(node)
            pause()

        elif choice == "2":
            if not nodes:
                pause()
                continue
            idx = IntPrompt.ask("Select node # to delete", default=1)
            if not (1 <= idx <= len(nodes)):
                console.print("[danger]Invalid selection.[/danger]")
                pause()
                continue
            node = nodes[idx - 1]
            if Confirm.ask(f"[warn]Delete node '{node.label}' and all its connections?[/warn]", default=False):
                db.delete(node)
                db.commit()
                rebuild_all(db)
                console.print("[accent]Deleted.[/accent]")
            pause()

        elif choice == "3":
            if not nodes:
                pause()
                continue
            idx = IntPrompt.ask("Select node # to rotate secrets for", default=1)
            if not (1 <= idx <= len(nodes)):
                console.print("[danger]Invalid selection.[/danger]")
                pause()
                continue
            node = nodes[idx - 1]
            psk, ppp = secrets_manager.issue_node_credentials(node)
            db.commit()
            rebuild_all(db)
            console.print(Panel(
                f"[warn bold]Shown only once — copy these now:[/warn bold]\n"
                f"PSK: [accent]{psk}[/accent]\nPPP Password: [accent]{ppp}[/accent]",
                border_style="warn",
            ))
            _prompt_save_script(node)
            pause()
            
        elif choice == "4":
            if not nodes:
                pause()
                continue
            idx = IntPrompt.ask("Select node # for setup script", default=1)
            if not (1 <= idx <= len(nodes)):
                console.print("[danger]Invalid selection.[/danger]")
                pause()
                continue
            node = nodes[idx - 1]
            _save_node_script(node)
            pause()


# ============================== 6) Connections & Routing ==============================

def menu_connections(db):
    while True:
        console.rule("[accent]Connections & Routing[/accent]")
        connections = db.query(Connection).order_by(Connection.id).all()
        nodes_by_id = {n.id: n for n in db.query(Node).all()}

        table = Table()
        table.add_column("#")
        table.add_column("Label")
        table.add_column("Source")
        table.add_column("Target")
        table.add_column("Mode")
        table.add_column("L7 Port")
        for i, c in enumerate(connections, 1):
            src = nodes_by_id.get(c.source_node_id)
            dst = nodes_by_id.get(c.target_node_id)
            table.add_row(
                str(i), c.label,
                src.label if src else "?", dst.label if dst else "?",
                c.mode.value, str(c.port) if c.enable_l7_proxy and c.port else "-",
            )
        console.print(table if connections else "[muted]No connections defined yet.[/muted]")

        console.print("\n1) Add connection\n2) Delete connection\n0) Back")
        choice = Prompt.ask("Choice", choices=["1", "2", "0"], default="0")
        if choice == "0":
            return

        if choice == "1":
            nodes = db.query(Node).order_by(Node.label).all()
            if len(nodes) < 2:
                console.print("[danger]You need at least 2 nodes to create a connection.[/danger]")
                pause()
                continue
            _print_nodes_table(nodes)
            label = Prompt.ask("Connection label (e.g. isf2teh)")
            src_idx = IntPrompt.ask("Source node #")
            dst_idx = IntPrompt.ask("Target node #")
            if not (1 <= src_idx <= len(nodes)) or not (1 <= dst_idx <= len(nodes)):
                console.print("[danger]Invalid node selection.[/danger]")
                pause()
                continue
            mode = Prompt.ask("Mode", choices=["two_way", "one_way"], default="two_way")
            enable_l7 = Confirm.ask("Also create a dedicated Nginx L7 proxy port for this route?", default=False)

            try:
                data = ConnectionCreate(
                    label=label,
                    source_node_id=nodes[src_idx - 1].id,
                    target_node_id=nodes[dst_idx - 1].id,
                    mode=ConnectionMode(mode),
                    enable_l7_proxy=enable_l7,
                )
            except (ValidationError, ValueError) as e:
                msg = e.errors()[0]["msg"] if isinstance(e, ValidationError) else str(e)
                console.print(f"[danger]{msg}[/danger]")
                pause()
                continue

            if db.query(Connection).filter(Connection.label == data.label).first():
                console.print(f"[danger]Label '{data.label}' is already in use.[/danger]")
                pause()
                continue

            port = find_free_port(db) if data.enable_l7_proxy else None
            connection = Connection(
                label=data.label, source_node_id=data.source_node_id,
                target_node_id=data.target_node_id, mode=data.mode,
                enable_l7_proxy=int(data.enable_l7_proxy), port=port,
            )
            db.add(connection)
            db.commit()
            rebuild_all(db)
            console.print(f"[accent]Connection '{data.label}' created.[/accent]" + (f" (port {port})" if port else ""))
            pause()

        elif choice == "2":
            if not connections:
                pause()
                continue
            idx = IntPrompt.ask("Select connection # to delete", default=1)
            if not (1 <= idx <= len(connections)):
                console.print("[danger]Invalid selection.[/danger]")
                pause()
                continue
            connection = connections[idx - 1]
            if Confirm.ask(f"Delete connection '{connection.label}'?", default=False):
                db.delete(connection)
                db.commit()
                rebuild_all(db)
                console.print("[accent]Deleted.[/accent]")
            pause()


# ============================== 7) Live Logs ==============================

def menu_live_logs():
    console.rule("[accent]Live Logs[/accent]")
    console.print("[muted]Streaming logs — press Ctrl+C to stop.[/muted]\n")
    try:
        for line in log_manager.follow_blocking():
            console.print(line, highlight=False)
    except KeyboardInterrupt:
        console.print("\n[muted]Log stream stopped.[/muted]")
    pause()


# ============================== 8) Settings (DEV/PROD) ==============================

def _read_env_dict() -> dict:
    """Parse the .env file into a dict."""
    data = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
    return data


def _write_env_dict(data: dict):
    """Write a dict back to the .env file."""
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in data.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n")


def menu_settings():
    while True:
        console.rule("[accent]Settings[/accent]")
        env_data = _read_env_dict()
        current_dev = env_data.get("PANEL_DEV_MODE", "1")
        is_dev = current_dev == "1"

        table = Table(show_header=False, box=None)
        table.add_column("Key", style="muted")
        table.add_column("Value")
        table.add_row(
            "DEV_MODE",
            f"[warn]ON (dry-run)[/warn]" if is_dev else "[accent]OFF (production)[/accent]"
        )
        table.add_row(
            ".env file",
            f"[accent]{ENV_FILE}[/accent]" if ENV_FILE.exists() else "[danger]not found[/danger]"
        )
        console.print(table)

        console.print(
            "\n1) Toggle DEV_MODE\n"
            "2) View full .env contents\n"
            "0) Back"
        )
        choice = Prompt.ask("Choice", choices=["1", "2", "0"], default="0")
        if choice == "0":
            return

        if choice == "1":
            new_val = "0" if is_dev else "1"
            label = "PRODUCTION" if is_dev else "DEVELOPMENT"

            if is_dev:
                # Switching to production — warn
                console.print(
                    "[warn]Switching to PRODUCTION mode means all config/firewall/service "
                    "changes will be applied to the real system (not dry-run).[/warn]"
                )
            else:
                console.print(
                    "[muted]Switching to DEVELOPMENT mode — system writes will be dry-run only.[/muted]"
                )

            if Confirm.ask(f"Set PANEL_DEV_MODE={new_val} ({label})?", default=True):
                env_data["PANEL_DEV_MODE"] = new_val
                _write_env_dict(env_data)
                console.print(f"[accent]PANEL_DEV_MODE set to {new_val}.[/accent]")
                console.print(
                    "[warn]This only takes effect for NEW processes: restart the panel "
                    "service AND exit/restart this CLI session (DEV_MODE can't hot-reload "
                    "in an already-running process).[/warn]"
                )
                if Confirm.ask("Restart the panel service now?", default=False):
                    console.print(systemd_manager.restart_service())
            pause()

        elif choice == "2":
            if ENV_FILE.exists():
                # Mask sensitive values for display
                console.print(Panel(
                    ENV_FILE.read_text(),
                    title=str(ENV_FILE),
                    border_style="muted",
                ))
            else:
                console.print("[danger].env file does not exist.[/danger]")
            pause()


# ============================== 9) Update ==============================

def menu_update():
    console.rule("[accent]Update[/accent]")
    if Confirm.ask("Update Python packages (pip install --upgrade -r requirements.txt)?", default=True):
        console.print(update_manager.update_python_packages())
    if Confirm.ask("Update system packages (nginx, xl2tpd, strongswan, ufw)?", default=True):
        console.print(update_manager.update_system_packages())
    pause()


# ============================== 10) Uninstall & Clean Slate ==============================

def menu_uninstall():
    console.rule("[danger]Uninstall & Clean Slate[/danger]")
    console.print(
        "[warn]This takes a safety backup first, then removes:\n"
        "  - Generated ipsec.conf / xl2tpd.conf / Nginx stream config\n"
        "  - The secrets directory (ipsec.secrets, chap-secrets)\n"
        "  - The custom iptables chain\n"
        "  - The panel's own systemd service\n"
        "The database itself and your backups are NOT deleted.[/warn]"
    )
    confirm_text = Prompt.ask("Type DELETE to confirm", default="")
    if confirm_text != "DELETE":
        console.print("[muted]Cancelled.[/muted]")
        pause()
        return
    result = uninstall_manager.clean_slate()
    console.print(result)
    pause()


# ============================== Main loop ==============================

def main():
    db = SessionLocal()
    try:
        if os.environ.get(INSTALL_RESUME_ENV) == "1":
            menu_install(resumed=True)

        while True:
            console.clear()
            banner()
            console.print(
                "\n[accent bold]i)[/accent bold] Install (Full Setup)\n"
                "1) Service Management\n"
                "2) Recovery & Security\n"
                "3) Network & Server\n"
                "4) Backup & Restore\n"
                "5) Node Management\n"
                "6) Connections & Routing\n"
                "7) Live Logs\n"
                "8) Settings (DEV/PROD)\n"
                "9) Update\n"
                "10) Uninstall & Clean Slate\n"
                "0) Exit\n"
            )
            valid = ["i", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
            choice = Prompt.ask("Select an option", choices=valid, default="0")

            if choice == "0":
                console.print("[muted]Bye.[/muted]")
                sys.exit(0)
            elif choice == "i":
                menu_install()
            elif choice == "1":
                menu_services()
            elif choice == "2":
                menu_recovery(db)
            elif choice == "3":
                menu_network(db)
            elif choice == "4":
                menu_backup()
            elif choice == "5":
                menu_nodes(db)
            elif choice == "6":
                menu_connections(db)
            elif choice == "7":
                menu_live_logs()
            elif choice == "8":
                menu_settings()
            elif choice == "9":
                menu_update()
            elif choice == "10":
                menu_uninstall()
    finally:
        db.close()


if __name__ == "__main__":
    main()
