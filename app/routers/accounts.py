from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user_optional, require_admin_api, require_admin_page, require_csrf_header
from ..flash import flash, pop_messages
from ..models import Song, User
from ..security import ensure_csrf, hash_password, verify_csrf, verify_password

router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates


@router.get("/login/", name="login")
def login_view(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user is not None:
        return RedirectResponse(url="/", status_code=303)
    csrf_token = ensure_csrf(request)
    return _templates(request).TemplateResponse(
        request, "accounts/login.html", {"error": None, "csrf_token": csrf_token}
    )


@router.post("/login/", name="login_submit")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    csrfmiddlewaretoken: str = Form(""),
    db: Session = Depends(get_db),
):
    error = None
    if not verify_csrf(request, csrfmiddlewaretoken):
        error = "Formulario caducado, inténtalo de nuevo."
    else:
        user = db.scalar(select(User).where(func.lower(User.username) == username.strip().lower()))
        if user and user.is_active and verify_password(password, user.password_hash):
            request.session.clear()
            request.session["user_id"] = user.id
            return RedirectResponse(url="/", status_code=303)
        error = "Usuario o contraseña incorrectos, o la cuenta está baneada."

    csrf_token = ensure_csrf(request)
    return _templates(request).TemplateResponse(
        request, "accounts/login.html", {"error": error, "csrf_token": csrf_token}
    )


@router.get("/logout/", name="logout")
def logout_view(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login/", status_code=303)


# ── Lógica de administración compartida entre el panel con formularios ──
# (fallback sin JS, recarga de página) y la API JSON (usada por el panel
# integrado en la SPA, que no recarga la página y no corta la música).


def _serialize_user(u: User) -> dict:
    """Requiere que u.song_count ya esté anotado (ver _list_users)."""
    return {
        "id": u.id,
        "username": u.username,
        "is_staff": u.is_staff,
        "is_active": u.is_active,
        "date_joined": u.date_joined.strftime("%d/%m/%Y"),
        "song_count": u.song_count,
    }


def _list_users(db: Session) -> list[User]:
    rows = db.execute(
        select(User, func.count(Song.id)).outerjoin(Song, Song.user_id == User.id).group_by(User.id).order_by(User.username)
    ).all()
    users = []
    for u, song_count in rows:
        u.song_count = song_count
        users.append(u)
    return users


def _do_create_user(db: Session, username: str, password: str, role: str) -> tuple[bool, str]:
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        return False, "El usuario y la contraseña son obligatorios."
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if db.scalar(select(User).where(func.lower(User.username) == username.lower())) is not None:
        return False, f"Ya existe un usuario llamado «{username}»."
    new_user = User(username=username, password_hash=hash_password(password), is_staff=(role == "admin"))
    db.add(new_user)
    db.commit()
    return True, f"Usuario «{new_user.username}» creado correctamente."


def _do_toggle_role(db: Session, actor: User, user_id: int) -> tuple[bool, str]:
    target = db.get(User, user_id)
    if target is None:
        return False, "Usuario no encontrado."
    if target.id == actor.id:
        return False, "No puedes cambiar tu propio rol."
    target.is_staff = not target.is_staff
    db.commit()
    return True, f"«{target.username}» ahora es {'admin' if target.is_staff else 'usuario'}."


def _do_toggle_ban(db: Session, actor: User, user_id: int) -> tuple[bool, str]:
    target = db.get(User, user_id)
    if target is None:
        return False, "Usuario no encontrado."
    if target.id == actor.id:
        return False, "No puedes banearte a ti mismo."
    target.is_active = not target.is_active
    db.commit()
    return True, f"«{target.username}» ha sido {'reactivado' if target.is_active else 'baneado'}."


def _do_set_password(db: Session, user_id: int, password: str) -> tuple[bool, str]:
    target = db.get(User, user_id)
    if target is None:
        return False, "Usuario no encontrado."
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    target.password_hash = hash_password(password)
    db.commit()
    return True, f"Contraseña de «{target.username}» actualizada."


def _do_delete_user(db: Session, actor: User, user_id: int) -> tuple[bool, str]:
    target = db.get(User, user_id)
    if target is None:
        return False, "Usuario no encontrado."
    if target.id == actor.id:
        return False, "No puedes eliminar tu propia cuenta."
    username = target.username
    db.delete(target)
    db.commit()
    return True, f"Usuario «{username}» eliminado (y su biblioteca de música)."


# ── Panel con formularios (fallback sin JS) ──────────────────────────


@router.get("/panel/", name="panel")
def panel(request: Request, user: User = Depends(require_admin_page), db: Session = Depends(get_db)):
    csrf_token = ensure_csrf(request)
    return _templates(request).TemplateResponse(
        request,
        "accounts/panel.html",
        {
            "users": _list_users(db),
            "user": user,
            "messages": pop_messages(request),
            "csrf_token": csrf_token,
        },
    )


def _check_csrf_or_flash(request: Request, token: str) -> bool:
    if not verify_csrf(request, token):
        flash(request, "Formulario caducado, inténtalo de nuevo.", "error")
        return False
    return True


@router.post("/panel/create", name="panel_create_user")
def create_user(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    role: str = Form("user"),
    csrfmiddlewaretoken: str = Form(""),
    user: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    if _check_csrf_or_flash(request, csrfmiddlewaretoken):
        ok, message = _do_create_user(db, username, password, role)
        flash(request, message, "success" if ok else "error")
    return RedirectResponse(url="/panel/", status_code=303)


@router.post("/panel/{user_id}/role", name="panel_toggle_role")
def toggle_role(
    request: Request,
    user_id: int,
    csrfmiddlewaretoken: str = Form(""),
    user: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    if _check_csrf_or_flash(request, csrfmiddlewaretoken):
        ok, message = _do_toggle_role(db, user, user_id)
        flash(request, message, "success" if ok else "error")
    return RedirectResponse(url="/panel/", status_code=303)


@router.post("/panel/{user_id}/ban", name="panel_toggle_ban")
def toggle_ban(
    request: Request,
    user_id: int,
    csrfmiddlewaretoken: str = Form(""),
    user: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    if _check_csrf_or_flash(request, csrfmiddlewaretoken):
        ok, message = _do_toggle_ban(db, user, user_id)
        flash(request, message, "success" if ok else "error")
    return RedirectResponse(url="/panel/", status_code=303)


@router.post("/panel/{user_id}/password", name="panel_set_password")
def set_password(
    request: Request,
    user_id: int,
    password: str = Form(""),
    csrfmiddlewaretoken: str = Form(""),
    user: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    if _check_csrf_or_flash(request, csrfmiddlewaretoken):
        ok, message = _do_set_password(db, user_id, password)
        flash(request, message, "success" if ok else "error")
    return RedirectResponse(url="/panel/", status_code=303)


@router.post("/panel/{user_id}/delete", name="panel_delete_user")
def delete_user(
    request: Request,
    user_id: int,
    csrfmiddlewaretoken: str = Form(""),
    user: User = Depends(require_admin_page),
    db: Session = Depends(get_db),
):
    if _check_csrf_or_flash(request, csrfmiddlewaretoken):
        ok, message = _do_delete_user(db, user, user_id)
        flash(request, message, "success" if ok else "error")
    return RedirectResponse(url="/panel/", status_code=303)


# ── API JSON (panel integrado en la SPA: no recarga la página, la música
# sigue sonando al navegar al panel de administración) ──────────────────


@router.get("/api/admin/users", name="admin_users_list")
def admin_users_list(user: User = Depends(require_admin_api), db: Session = Depends(get_db)):
    return JSONResponse({"users": [_serialize_user(u) for u in _list_users(db)]})


@router.post("/api/admin/users", name="admin_create_user", dependencies=[Depends(require_csrf_header)])
def admin_create_user(
    payload: dict,
    user: User = Depends(require_admin_api),
    db: Session = Depends(get_db),
):
    ok, message = _do_create_user(db, payload.get("username", ""), payload.get("password", ""), payload.get("role", "user"))
    return JSONResponse({"success": ok, "message": message}, status_code=200 if ok else 400)


@router.post("/api/admin/users/{user_id}/role", name="admin_toggle_role", dependencies=[Depends(require_csrf_header)])
def admin_toggle_role(user_id: int, user: User = Depends(require_admin_api), db: Session = Depends(get_db)):
    ok, message = _do_toggle_role(db, user, user_id)
    return JSONResponse({"success": ok, "message": message}, status_code=200 if ok else 400)


@router.post("/api/admin/users/{user_id}/ban", name="admin_toggle_ban", dependencies=[Depends(require_csrf_header)])
def admin_toggle_ban(user_id: int, user: User = Depends(require_admin_api), db: Session = Depends(get_db)):
    ok, message = _do_toggle_ban(db, user, user_id)
    return JSONResponse({"success": ok, "message": message}, status_code=200 if ok else 400)


@router.post("/api/admin/users/{user_id}/password", name="admin_set_password", dependencies=[Depends(require_csrf_header)])
def admin_set_password(
    user_id: int,
    payload: dict,
    user: User = Depends(require_admin_api),
    db: Session = Depends(get_db),
):
    ok, message = _do_set_password(db, user_id, payload.get("password", ""))
    return JSONResponse({"success": ok, "message": message}, status_code=200 if ok else 400)


@router.post("/api/admin/users/{user_id}/delete", name="admin_delete_user", dependencies=[Depends(require_csrf_header)])
def admin_delete_user(user_id: int, user: User = Depends(require_admin_api), db: Session = Depends(get_db)):
    ok, message = _do_delete_user(db, user, user_id)
    return JSONResponse({"success": ok, "message": message}, status_code=200 if ok else 400)
