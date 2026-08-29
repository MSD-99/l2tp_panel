from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.i18n import translate
from app.models import User
from app.security import require_admin_web
from app.services import backup_manager, cron_manager
from app.templates_env import templates

router = APIRouter(prefix="/backup", tags=["backup"])


def _lang(request: Request) -> str:
    return getattr(request.state, "lang", "fa")


@router.get("", response_class=HTMLResponse)
def backup_page(request: Request, user: User = Depends(require_admin_web)):
    return templates.TemplateResponse(
        "backup.html",
        {
            "request": request, "user": user, "active": "backup",
            "backups": backup_manager.list_backups(),
            "cron_enabled": cron_manager.cron_status(),
            "message": None,
        },
    )


@router.post("/create")
def create_backup_now(request: Request, user: User = Depends(require_admin_web)):
    result = backup_manager.create_backup(triggered_by="manual")
    msg = translate("msg_backup_created", _lang(request)).format(
        filename=result["filename"], size_kb=result["size_kb"]
    )
    return templates.TemplateResponse(
        "backup.html",
        {
            "request": request, "user": user, "active": "backup",
            "backups": backup_manager.list_backups(),
            "cron_enabled": cron_manager.cron_status(),
            "message": msg,
        },
    )


@router.post("/restore")
def restore_backup_now(request: Request, filename: str = Form(...), user: User = Depends(require_admin_web)):
    lang = _lang(request)
    try:
        result = backup_manager.restore_backup(filename)
        if result.get("applied"):
            msg = translate("msg_restore_done", lang).format(filename=filename)
        else:
            msg = translate("msg_restore_dryrun", lang)
    except FileNotFoundError:
        msg = translate("err_backup_not_found", lang)

    return templates.TemplateResponse(
        "backup.html",
        {
            "request": request, "user": user, "active": "backup",
            "backups": backup_manager.list_backups(),
            "cron_enabled": cron_manager.cron_status(),
            "message": msg,
        },
    )


@router.post("/cron/enable")
def enable_cron(user: User = Depends(require_admin_web)):
    cron_manager.enable_cron_backup()
    return RedirectResponse(url="/backup", status_code=303)


@router.post("/cron/disable")
def disable_cron(user: User = Depends(require_admin_web)):
    cron_manager.disable_cron_backup()
    return RedirectResponse(url="/backup", status_code=303)
