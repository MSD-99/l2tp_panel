from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.i18n import translate
from app.models import User
from app.security import require_admin_web
from app.services import systemd_manager
from app.services.orchestrator import rebuild_all
from app.templates_env import templates

router = APIRouter(prefix="/system", tags=["system"])


@router.get("", response_class=HTMLResponse)
def system_page(request: Request, user: User = Depends(require_admin_web)):
    return templates.TemplateResponse(
        "system.html",
        {
            "request": request, "user": user, "active": "system",
            "status": systemd_manager.service_status(),
            "service_preview": systemd_manager.build_service_file(),
            "message": None,
        },
    )


@router.post("/service/enable")
def enable_service(user: User = Depends(require_admin_web)):
    systemd_manager.enable_service()
    return RedirectResponse(url="/system", status_code=303)


@router.post("/service/disable")
def disable_service(user: User = Depends(require_admin_web)):
    systemd_manager.disable_service()
    return RedirectResponse(url="/system", status_code=303)


@router.post("/rebuild-now")
def rebuild_now(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin_web)):
    result = rebuild_all(db)
    return templates.TemplateResponse(
        "system.html",
        {
            "request": request, "user": user, "active": "system",
            "status": systemd_manager.service_status(),
            "service_preview": systemd_manager.build_service_file(),
            "message": translate("msg_configs_rebuilt", getattr(request.state, "lang", "fa")),
            "rebuild_result": result,
        },
    )
