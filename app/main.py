from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import Base, engine
from app import models  # noqa: F401  (register models on Base metadata)
from app.security import NotAuthenticatedWeb
from app.settings import load_settings
from app.routers import auth, nodes, connections, dashboard, backup, system, users, logs, api
from app.routers.auth import LOGIN_PATH

Base.metadata.create_all(bind=engine)

SUPPORTED_LANGS = ("fa", "en")


class LocaleMiddleware(BaseHTTPMiddleware):
    """Reads ?lang=fa|en (persisted to a cookie) or falls back to the
    existing cookie, defaulting to Persian. Exposes it as request.state.lang
    so templates can call t('key') without every route wiring it manually."""

    async def dispatch(self, request: Request, call_next):
        requested = request.query_params.get("lang")
        if requested in SUPPORTED_LANGS:
            lang = requested
        else:
            lang = request.cookies.get("lang", "fa")
            if lang not in SUPPORTED_LANGS:
                lang = "fa"
        request.state.lang = lang

        response = await call_next(request)

        if requested in SUPPORTED_LANGS:
            response.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365)
        return response


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import SessionLocal
    from app.services.orchestrator import rebuild_all
    db = SessionLocal()
    try:
        rebuild_all(db)
    finally:
        db.close()
    yield

app = FastAPI(title="Central Routing Manager Panel", lifespan=lifespan)
app.add_middleware(LocaleMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth.router)
app.include_router(nodes.router)
app.include_router(connections.router)
app.include_router(dashboard.router)
app.include_router(backup.router)
app.include_router(system.router)
app.include_router(users.router)
app.include_router(logs.router)
app.include_router(api.router)


@app.exception_handler(NotAuthenticatedWeb)
def not_authenticated_handler(request: Request, exc: NotAuthenticatedWeb):
    return RedirectResponse(url=LOGIN_PATH)


@app.get("/")
def root():
    return RedirectResponse(url=LOGIN_PATH)


# A tiny inline favicon so browsers stop 404-ing on it in the access logs.
_FAVICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="6" fill="#0d1117"/>
<circle cx="8" cy="16" r="3" fill="#45d8c4"/>
<circle cx="24" cy="16" r="3" fill="#45d8c4"/>
<line x1="11" y1="16" x2="21" y2="16" stroke="#45d8c4" stroke-width="2" stroke-dasharray="2,2"/>
</svg>"""


@app.get("/favicon.ico")
def favicon():
    return Response(content=_FAVICON_SVG, media_type="image/svg+xml")
