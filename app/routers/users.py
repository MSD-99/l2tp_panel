from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.i18n import translate
from app.models import User, UserRole
from app.schemas import UserCreate
from app.security import require_admin_web, hash_password
from app.templates_env import templates

router = APIRouter(prefix="/users", tags=["users"])


def _lang(request: Request) -> str:
    return getattr(request.state, "lang", "fa")


@router.get("", response_class=HTMLResponse)
def list_users(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin_web)):
    users = db.query(User).order_by(User.id).all()
    return templates.TemplateResponse(
        "users_list.html",
        {"request": request, "user": user, "active": "users", "users": users},
    )


@router.get("/new", response_class=HTMLResponse)
def new_user_form(request: Request, user: User = Depends(require_admin_web)):
    return templates.TemplateResponse(
        "user_form.html",
        {"request": request, "user": user, "active": "users", "errors": []},
    )


@router.post("/new")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_web),
):
    try:
        data = UserCreate(username=username, password=password, role=UserRole(role))
    except (ValidationError, ValueError) as e:
        # Pydantic validator messages are English-only (see schemas.py)
        errors = [err["msg"] for err in e.errors()] if isinstance(e, ValidationError) else [str(e)]
        return templates.TemplateResponse(
            "user_form.html",
            {"request": request, "user": user, "active": "users", "errors": errors},
            status_code=422,
        )

    if db.query(User).filter(User.username == data.username).first():
        errors = [translate("err_username_taken", _lang(request)).format(value=data.username)]
        return templates.TemplateResponse(
            "user_form.html",
            {"request": request, "user": user, "active": "users", "errors": errors},
            status_code=422,
        )

    new_user = User(username=data.username, password_hash=hash_password(data.password), role=data.role)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/users", status_code=303)


@router.post("/{user_id}/delete")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin_web)):
    lang = _lang(request)
    target = db.query(User).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail=translate("err_user_not_found", lang))
    if target.id == user.id:
        raise HTTPException(status_code=400, detail=translate("err_cannot_delete_self", lang))
    if target.role == UserRole.admin:
        admin_count = db.query(User).filter(User.role == UserRole.admin).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail=translate("err_cannot_delete_last_admin", lang))

    db.delete(target)
    db.commit()
    return RedirectResponse(url="/users", status_code=303)
