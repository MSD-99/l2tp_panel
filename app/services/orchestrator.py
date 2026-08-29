from sqlalchemy.orm import Session

from app.models import Node, Connection
from app.services import secrets_manager, config_generator, firewall


def rebuild_all(db: Session) -> dict:
    nodes = db.query(Node).all()
    connections = db.query(Connection).all()
    nodes_by_id = {n.id: n for n in nodes}

    secrets_result = secrets_manager.rebuild_secret_files(nodes)
    configs_result = config_generator.rebuild_all_configs(nodes, connections)
    firewall_result = firewall.apply_rules(connections, nodes_by_id)

    from app.services import service_control
    service_result = {}
    if not __import__("app.config").config.DEV_MODE:
        import subprocess
        # Seamlessly reload IPsec without dropping active tunnels
        subprocess.run(["ipsec", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["ipsec", "rereadsecrets"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        service_result["ipsec"] = {"status": "reloaded seamlessly"}
        
        # xl2tpd configuration (other than comments) is static, and pppd reads chap-secrets dynamically.
        # No need to restart xl2tpd, preventing tunnel drops!
        service_result["xl2tpd"] = {"status": "skipped restart (seamless)"}
        
        service_result["nginx"] = service_control.service_action("nginx", "reload")

    return {
        "secrets": secrets_result,
        "configs": configs_result,
        "firewall": firewall_result,
        "services": service_result,
    }
