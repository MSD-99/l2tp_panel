import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from app.models import User
from app.security import require_admin_web, get_current_user
from app.services import log_manager
from app.templates_env import templates

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_class=HTMLResponse)
def logs_page(request: Request, user: User = Depends(require_admin_web)):
    initial_lines = log_manager.tail_lines(100)
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request, "user": user, "active": "logs",
            "initial_lines": initial_lines,
        },
    )


@router.get("/stream")
async def log_stream(request: Request, user: User = Depends(get_current_user)):
    """SSE endpoint: streams live log lines to the browser."""
    async def event_generator():
        async for line in log_manager.stream_lines():
            if await request.is_disconnected():
                break
            yield {"event": "log", "data": line}

    return EventSourceResponse(event_generator())


@router.get("/node/{node_id}/stream")
async def node_log_stream(node_id: int, request: Request, user: User = Depends(get_current_user)):
    """SSE endpoint: streams VPN/System log lines specific to a node."""
    from app.database import SessionLocal
    from app.models import Node
    db = SessionLocal()
    node = db.query(Node).get(node_id)
    db.close()
    
    if not node:
        return HTMLResponse("Node not found", status_code=404)

    async def event_generator():
        async for line in log_manager.stream_node_lines(node.label, node.tunnel_ip):
            if await request.is_disconnected():
                break
            yield {"event": "log", "data": line}

    return EventSourceResponse(event_generator())
