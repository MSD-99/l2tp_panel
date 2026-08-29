from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.i18n import translate
from app.models import Node, Connection, User, ConnectionMode
from app.schemas import ConnectionCreate
from app.security import get_web_user, require_admin_web
from app.services.port_allocator import find_free_port
from app.services.orchestrator import rebuild_all
from app.templates_env import templates

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_class=HTMLResponse)
def list_connections(request: Request, db: Session = Depends(get_db), user: User = Depends(get_web_user)):
    connections = db.query(Connection).order_by(Connection.id).all()
    nodes_by_id = {n.id: n for n in db.query(Node).all()}
    return templates.TemplateResponse(
        "connections_list.html",
        {"request": request, "user": user, "active": "connections",
         "connections": connections, "nodes_by_id": nodes_by_id},
    )


@router.get("/new", response_class=HTMLResponse)
def new_connection_form(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin_web)):
    nodes = db.query(Node).order_by(Node.label).all()
    return templates.TemplateResponse(
        "connection_form.html",
        {"request": request, "user": user, "active": "connections", "nodes": nodes, "errors": []},
    )


@router.post("/new")
def create_connection(
    request: Request,
    label: str = Form(...),
    source_node_id: int = Form(...),
    target_node_id: int = Form(...),
    mode: str = Form(...),
    enable_l7_proxy: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_web),
):
    nodes = db.query(Node).order_by(Node.label).all()

    try:
        data = ConnectionCreate(
            label=label,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            mode=ConnectionMode(mode),
            enable_l7_proxy=enable_l7_proxy,
        )
    except (ValidationError, ValueError) as e:
        errors = [str(e)] if isinstance(e, ValueError) and not isinstance(e, ValidationError) else [
            err["msg"] for err in e.errors()
        ]
        return templates.TemplateResponse(
            "connection_form.html",
            {"request": request, "user": user, "active": "connections", "nodes": nodes, "errors": errors},
            status_code=422,
        )

    if db.query(Connection).filter(Connection.label == data.label).first():
        lang = getattr(request.state, "lang", "fa")
        return templates.TemplateResponse(
            "connection_form.html",
            {"request": request, "user": user, "active": "connections", "nodes": nodes,
             "errors": [translate("err_connection_label_taken", lang).format(value=data.label)]},
            status_code=422,
        )

    port = None
    if data.enable_l7_proxy:
        port = find_free_port(db)

    connection = Connection(
        label=data.label,
        source_node_id=data.source_node_id,
        target_node_id=data.target_node_id,
        mode=data.mode,
        enable_l7_proxy=int(data.enable_l7_proxy),
        port=port,
    )
    db.add(connection)
    db.commit()

    rebuild_all(db)
    return RedirectResponse(url="/connections", status_code=303)


@router.post("/{connection_id}/delete")
def delete_connection(connection_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin_web)):
    connection = db.query(Connection).get(connection_id)
    if connection:
        db.delete(connection)
        db.commit()
        rebuild_all(db)
    return RedirectResponse(url="/connections", status_code=303)
