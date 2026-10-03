from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import verify_csrf


class RedirectToLogin(Exception):
    """Página protegida sin sesión: redirige a /login/ (equivalente a @login_required)."""


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        request.session.clear()
        return None
    return user


def require_user_page(user: User | None = Depends(get_current_user_optional)) -> User:
    """Para rutas de página: si no hay sesión, redirige a /login/."""
    if user is None:
        raise RedirectToLogin()
    return user


def require_user_api(user: User | None = Depends(get_current_user_optional)) -> User:
    """Para rutas JSON: si no hay sesión, 401 (el frontend ya maneja ese status)."""
    if user is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user


def require_admin_page(user: User = Depends(require_user_page)) -> User:
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Solo administradores pueden acceder a esta página.")
    return user


def require_admin_api(user: User = Depends(require_user_api)) -> User:
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Solo administradores pueden realizar esta acción.")
    return user


def redirect_to_login_handler(request: Request, exc: RedirectToLogin):
    return RedirectResponse(url="/login/", status_code=303)


def require_csrf_header(request: Request) -> None:
    """Para endpoints JSON que mutan estado: valida X-CSRFToken (igual que CsrfViewMiddleware)."""
    token = request.headers.get("x-csrftoken")
    if not verify_csrf(request, token):
        raise HTTPException(status_code=403, detail="CSRF token inválido o ausente")
