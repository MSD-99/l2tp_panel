from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import verify_password, create_access_token, get_current_user
from app.settings import load_settings
from app.templates_env import templates

_settings = load_settings()
LOGIN_PATH = _settings["login_path"]

router = APIRouter(tags=["auth"])


@router.get(LOGIN_PATH, response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error_key": None})


@router.post(LOGIN_PATH)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error_key": "login_error"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = create_access_token({"sub": user.username, "role": user.role.value})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=(request.url.scheme == "https"),
        max_age=60 * 60 * 8,
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(url=LOGIN_PATH, status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response


@router.get("/api/auth/me")
def whoami(user: User = Depends(get_current_user)):
    return {"username": user.username, "role": user.role.value}
