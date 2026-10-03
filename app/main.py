from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import config
from .database import init_db
from .deps import RedirectToLogin, redirect_to_login_handler
from .routers import accounts, music

BASE_DIR = config.BASE_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Sonara", docs_url=None, redoc_url=None, lifespan=lifespan)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS + ["127.0.0.1", "localhost"])

app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie="sonara_session",
    same_site="lax",
    https_only=config.SESSION_COOKIE_SECURE,
)

app.add_exception_handler(RedirectToLogin, redirect_to_login_handler)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["dateformat"] = lambda d: d.strftime("%d/%m/%Y") if d else ""
app.state.templates = templates

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(accounts.router)
app.include_router(music.router)


@app.get("/sw.js")
def service_worker():
    body = (BASE_DIR / "static" / "sw.js").read_text(encoding="utf-8")
    return PlainTextResponse(
        body,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Service-Worker-Allowed": "/",
        },
    )
