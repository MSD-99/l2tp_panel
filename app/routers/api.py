from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Node, Connection
from app.crypto_utils import decrypt_str

router = APIRouter(prefix="/api/v1", tags=["api"])

@router.get("/routes/{node_id}", response_class=PlainTextResponse)
def get_node_routes(node_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    """
    Returns a plain text list of CIDRs that this node should route through the L2TP tunnel.
    Authenticated via the node's PSK in the Authorization header.
    """
    node = db.query(Node).get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    if not node.encrypted_psk:
        raise HTTPException(status_code=401, detail="Node has no credentials")
        
    actual_psk = decrypt_str(node.encrypted_psk)
    
    # Check Authorization: Bearer {psk}
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split("Bearer ")[1].strip()
    
    if token != actual_psk:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    routes = set()
    # Always route the VPN subnet itself
    routes.add("10.10.10.0/24")
    
    # Find all connections involving this node
    connections = db.query(Connection).filter(
        (Connection.source_node_id == node.id) | (Connection.target_node_id == node.id)
    ).all()
    
    # Load all nodes into a dict for quick lookup
    all_nodes = {n.id: n for n in db.query(Node).all()}
    
    for c in connections:
        if c.source_node_id == node.id:
            # We are the source. We need to reach the target's subnet.
            target_node = all_nodes.get(c.target_node_id)
            if target_node and target_node.subnet_cidr:
                routes.add(target_node.subnet_cidr)
        elif c.target_node_id == node.id:
            # We are the target. We ALWAYS need to route to the source's subnet, 
            # even in one-way mode, so we can return packets (SYN-ACK, etc).
            # The actual traffic restriction is enforced by the central server firewall.
            source_node = all_nodes.get(c.source_node_id)
            if source_node and source_node.subnet_cidr:
                routes.add(source_node.subnet_cidr)
                
    # Return as newline separated string
    return "\n".join(sorted(routes))
