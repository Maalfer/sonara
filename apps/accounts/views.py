from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

User = get_user_model()


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    error = None
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/")
        error = "Usuario o contraseña incorrectos, o la cuenta está baneada."

    return render(request, "accounts/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden("Solo administradores pueden acceder a esta página.")
        return view(request, *args, **kwargs)
    return wrapped


@admin_required
def panel(request):
    users = User.objects.annotate(song_count=Count("songs")).order_by("username")
    return render(request, "accounts/panel.html", {"users": users})


@admin_required
@require_POST
def create_user(request):
    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""
    role = request.POST.get("role") or "user"

    if not username or not password:
        messages.error(request, "El usuario y la contraseña son obligatorios.")
    elif len(password) < 8:
        messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
    elif User.objects.filter(username__iexact=username).exists():
        messages.error(request, f"Ya existe un usuario llamado «{username}».")
    else:
        user = User(username=username, is_staff=(role == "admin"))
        user.set_password(password)
        user.save()
        messages.success(request, f"Usuario «{user.username}» creado correctamente.")

    return redirect("panel")


@admin_required
@require_POST
def toggle_role(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, "No puedes cambiar tu propio rol.")
        return redirect("panel")
    target.is_staff = not target.is_staff
    target.save(update_fields=["is_staff"])
    messages.success(request, f"«{target.username}» ahora es {'admin' if target.is_staff else 'usuario'}.")
    return redirect("panel")


@admin_required
@require_POST
def toggle_ban(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, "No puedes banearte a ti mismo.")
        return redirect("panel")
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    messages.success(request, f"«{target.username}» ha sido {'reactivado' if target.is_active else 'baneado'}.")
    return redirect("panel")


@admin_required
@require_POST
def set_password(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    password = request.POST.get("password") or ""
    if len(password) < 8:
        messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
    else:
        target.set_password(password)
        target.save(update_fields=["password"])
        messages.success(request, f"Contraseña de «{target.username}» actualizada.")
    return redirect("panel")


@admin_required
@require_POST
def delete_user(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta.")
        return redirect("panel")
    username = target.username
    target.delete()
    messages.success(request, f"Usuario «{username}» eliminado (y su biblioteca de música).")
    return redirect("panel")
