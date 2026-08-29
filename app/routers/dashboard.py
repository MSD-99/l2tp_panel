from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import DEV_MODE
from app.database import get_db
from app.models import Node, Connection, User
from app.security import get_web_user
from app.services.network_utils import ping
from app.services.metrics import get_system_metrics
from app.templates_env import templates

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_web_user)):
    nodes = db.query(Node).order_by(Node.id).all()
    connections = db.query(Connection).order_by(Connection.id).all()
    nodes_by_id = {n.id: n for n in nodes}

    node_status = [{"node": n, "online": ping(n.tunnel_ip)} for n in nodes]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request, "user": user, "active": "dashboard",
            "node_status": node_status, "connections": connections,
            "nodes_by_id": nodes_by_id, "dev_mode": DEV_MODE,
        },
    )

@router.get("/api/system/metrics")
def api_system_metrics(user: User = Depends(get_web_user)):
    """Returns current CPU, RAM, and Disk usage."""
    return get_system_metrics()
