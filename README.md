# Central Routing Manager (L2TP/IPsec Panel)

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Production_Ready-success)

A modern, high-performance, centralized orchestration panel for managing L2TP/IPsec VPN nodes, dynamic routing, and network relays. Designed for enterprise-grade scalability with a **zero-downtime** seamless reload architecture.

---

## 🚀 Key Features

- **Centralized Hub & Spoke Architecture:** Manage a fleet of remote Linux servers (nodes) entirely from a single central dashboard.
- **Zero-Downtime Reloads (Seamless):** Adding nodes or reconfiguring routes dynamically reloads IPsec SAs and secrets without dropping active connections.
- **Automated Node Provisioning:** Generate 1-click bash scripts from the panel to automatically configure strongSwan, xl2tpd, and dynamic routing on remote nodes.
- **Dynamic L2TP Routing:** Nodes automatically pull their desired subnets from the Central API and apply them dynamically over the `ppp0` interface.
- **L7 Reverse Proxy & Relaying:** Integrated Nginx Stream module for one-way or two-way TCP port forwarding and relaying between connected nodes.
- **Automated Security & Firewall:** The panel dynamically configures UFW on the central server to strictly allow traffic only from authenticated node IPs.
- **Built-in CLI Tool:** Includes an interactive command-line interface (`l2tp`) for emergency recovery, manual backups, and service management without using the web UI.

## 🛠 Tech Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite
- **Frontend:** HTML5, Jinja2, Vanilla CSS (Glassmorphism & Dark Mode)
- **Networking:** strongSwan (IPsec IKEv2), xl2tpd, pppd, iptables, ufw
- **Proxy:** Nginx (Stream module)

---

## ⚙️ Installation (Central Server)

The installation process is fully automated. Run the following on a clean Ubuntu 22.04/24.04 server:

```bash
git clone https://github.com/MSD-99/l2tp_panel.git
cd l2tp_panel
sudo bash install.sh
```

**What the installer does:**
1. Installs system dependencies (`strongswan`, `xl2tpd`, `nginx`, `ufw`, `python3-venv`).
2. Generates cryptographic keys and production `.env` variables.
3. Sets up the SQLite database and prompts you to create an initial Web Admin.
4. Secures the server using `ufw` (opening only SSH and Panel ports initially).
5. Configures systemd services and registers the `l2tp` CLI command.

Once installed, navigate to:
`http://<SERVER_IP>:8000/login`

---

## 🖥 Managing Nodes

1. **Add a Node:** Log into the Web Panel and add a new node (providing its Public IP and optionally a Subnet CIDR).
2. **Setup the Remote Server:** Click the **"Setup Script"** button next to the newly created node. Copy the one-line bash script.
3. **Deploy:** SSH into your remote node (spoke server) and paste the script. It will automatically install IPsec/L2TP, authenticate with the Central Server, and establish a permanent tunnel.
4. **Relay & Routing:** Go to the "Connections" tab to establish one-way or two-way relays between any of your authenticated nodes. The central server handles all iptables NAT and Nginx routing automatically.

---

## 🔧 CLI Management

The project ships with an interactive CLI tool. At any time on the central server, simply type:

```bash
l2tp
```

**Available Options:**
- `1` **Service Management:** Start/Stop/Restart services (ipsec, xl2tpd, nginx, panel).
- `2` **Recovery & Security:** Reset admin passwords or rotate JWT secrets.
- `3` **Network & Server:** View live firewall rules, tunnel interfaces, and IP routes.
- `4` **Backup & Restore:** Create manual database backups or restore from archives.
- `7` **Live Logs:** Stream syslog or panel logs in real-time.

---

## 🔒 Security Posture

- **IKEv2 IPsec:** All L2TP traffic is encapsulated in highly secure IKEv2 IPsec tunnels using `AES_CBC_256/HMAC_SHA2_256_128`.
- **Dynamic Firewalling:** The orchestrator strictly limits UDP `500/4500` and `1701` ports to the public IPs of registered nodes.
- **API Authentication:** Nodes communicate with the Central API using their uniquely generated Pre-Shared Keys (PSK) via Bearer tokens.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
