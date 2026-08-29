import subprocess

from app.config import DEV_MODE
from app.models import Connection, Node

CHAIN_NAME = "CENTRAL_ROUTES"


def _run(cmd: list[str]) -> tuple[int, str]:
    if DEV_MODE:
        return 0, "(dry-run, command not executed)"
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, (result.stdout or result.stderr)


def build_rules(connections: list[Connection], nodes_by_id: dict[int, Node]) -> list[str]:
    """
    Returns the rules as iptables command strings (for preview/review), also
    ready to execute. Since the CIDRs were already validated with ipaddress
    in schemas.py, it's safe to interpolate them directly into the command.
    """
    rules = [
        f"iptables -N {CHAIN_NAME} 2>/dev/null",  # create the chain if it does not exist yet
        f"iptables -F {CHAIN_NAME}",               # clear old rules for a clean rebuild
        f"iptables -A {CHAIN_NAME} -m state --state ESTABLISHED,RELATED -j ACCEPT", # Allow return traffic
    ]

    for c in connections:
        src = nodes_by_id.get(c.source_node_id)
        dst = nodes_by_id.get(c.target_node_id)
        if not src or not dst:
            continue

        src_ip = src.subnet_cidr if src.subnet_cidr else src.tunnel_ip
        dst_ip = dst.subnet_cidr if dst.subnet_cidr else dst.tunnel_ip

        rules.append(f"# Route: {c.label} ({c.mode.value})")
        # Subnet rules
        rules.append(f"iptables -A {CHAIN_NAME} -s {src_ip} -d {dst_ip} -j ACCEPT")
        rules.append(f"ip route replace {dst_ip} via {dst.tunnel_ip} 2>/dev/null || true")
        # Tunnel IP rules (always allow node-to-node tunnel IP communication)
        rules.append(f"iptables -A {CHAIN_NAME} -s {src.tunnel_ip} -d {dst.tunnel_ip} -j ACCEPT")

        if c.mode.value == "two_way":
            rules.append(f"iptables -A {CHAIN_NAME} -s {dst_ip} -d {src_ip} -j ACCEPT")
            rules.append(f"ip route replace {src_ip} via {src.tunnel_ip} 2>/dev/null || true")
            rules.append(f"iptables -A {CHAIN_NAME} -s {dst.tunnel_ip} -d {src.tunnel_ip} -j ACCEPT")
        # one_way mode: the return rule is deliberately NOT added - only src -> dst is allowed

    rules.append(f"iptables -A {CHAIN_NAME} -j DROP")  # default: drop anything not explicitly allowed

    # Hook the custom chain into FORWARD only for PPP interfaces (to not drop other forwarding traffic)
    rules.append(f"iptables -D FORWARD -i ppp+ -j {CHAIN_NAME} 2>/dev/null || true")
    rules.append(f"iptables -I FORWARD 1 -i ppp+ -j {CHAIN_NAME}")
    rules.append(f"iptables -D FORWARD -o ppp+ -j {CHAIN_NAME} 2>/dev/null || true")
    rules.append(f"iptables -I FORWARD 2 -o ppp+ -j {CHAIN_NAME}")

    # Add SNAT/Masquerade so nodes don't need asymmetric return routes
    rules.append(
        "iptables -t nat -C POSTROUTING -o ppp+ -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -o ppp+ -j MASQUERADE"
    )
    return rules


def apply_rules(connections: list[Connection], nodes_by_id: dict[int, Node]) -> dict:
    rule_strings = build_rules(connections, nodes_by_id)
    logs = []
    
    # Ensure IP forwarding is enabled at the OS level
    _run(["sysctl", "-w", "net.ipv4.ip_forward=1"])
    
    for rule in rule_strings:
        if rule.startswith("#"):
            logs.append(rule)
            continue
        code, output = _run(["bash", "-c", rule])
        logs.append(f"$ {rule}\n  -> exit={code} {output.strip()}")

    return {"applied": not DEV_MODE, "rules": rule_strings, "logs": logs}
