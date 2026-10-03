from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user_optional, require_admin_page
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


@router.get("/panel/", name="panel")
def panel(request: Request, user: User = Depends(require_admin_page), db: Session = Depends(get_db)):
    rows = db.execute(
        select(User, func.count(Song.id)).outerjoin(Song, Song.user_id == User.id).group_by(User.id).order_by(User.username)
    ).all()
    users = []
    for u, song_count in rows:
        u.song_count = song_count
        users.append(u)
    csrf_token = ensure_csrf(request)
    return _templates(request).TemplateResponse(
        request,
        "accounts/panel.html",
        {
            "users": users,
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
        username = username.strip()
        existing = db.scalar(select(User).where(func.lower(User.username) == username.lower()))
        if not username or not password:
            flash(request, "El usuario y la contraseña son obligatorios.", "error")
        elif len(password) < 8:
            flash(request, "La contraseña debe tener al menos 8 caracteres.", "error")
        elif existing is not None:
            flash(request, f"Ya existe un usuario llamado «{username}».", "error")
        else:
            new_user = User(username=username, password_hash=hash_password(password), is_staff=(role == "admin"))
            db.add(new_user)
            db.commit()
            flash(request, f"Usuario «{new_user.username}» creado correctamente.", "success")
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
        target = db.get(User, user_id)
        if target is None:
            flash(request, "Usuario no encontrado.", "error")
        elif target.id == user.id:
            flash(request, "No puedes cambiar tu propio rol.", "error")
        else:
            target.is_staff = not target.is_staff
            db.commit()
            flash(request, f"«{target.username}» ahora es {'admin' if target.is_staff else 'usuario'}.", "success")
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
        target = db.get(User, user_id)
        if target is None:
            flash(request, "Usuario no encontrado.", "error")
        elif target.id == user.id:
            flash(request, "No puedes banearte a ti mismo.", "error")
        else:
            target.is_active = not target.is_active
            db.commit()
            flash(request, f"«{target.username}» ha sido {'reactivado' if target.is_active else 'baneado'}.", "success")
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
        target = db.get(User, user_id)
        if target is None:
            flash(request, "Usuario no encontrado.", "error")
        elif len(password) < 8:
            flash(request, "La contraseña debe tener al menos 8 caracteres.", "error")
        else:
            target.password_hash = hash_password(password)
            db.commit()
            flash(request, f"Contraseña de «{target.username}» actualizada.", "success")
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
        target = db.get(User, user_id)
        if target is None:
            flash(request, "Usuario no encontrado.", "error")
        elif target.id == user.id:
            flash(request, "No puedes eliminar tu propia cuenta.", "error")
        else:
            username = target.username
            db.delete(target)
            db.commit()
            flash(request, f"Usuario «{username}» eliminado (y su biblioteca de música).", "success")
    return RedirectResponse(url="/panel/", status_code=303)
