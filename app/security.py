"""Hash de contraseñas (PBKDF2-SHA256, stdlib) y tokens CSRF — sin dependencias de Django.

Formato de hash idéntico al de django.contrib.auth (pbkdf2_sha256$iteraciones$salt$hash
en base64), para poder migrar usuarios existentes sin tener que resetear su contraseña.
"""
import base64
import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    b64_digest = base64.b64encode(digest).decode()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${b64_digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iterations, salt, b64_digest = encoded.split("$")
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations)
    except (ValueError, AttributeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return hmac.compare_digest(base64.b64encode(digest).decode(), b64_digest)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def ensure_csrf(request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = new_csrf_token()
        request.session["csrf_token"] = token
    return token


def verify_csrf(request, token: str | None) -> bool:
    expected = request.session.get("csrf_token")
    return bool(expected) and bool(token) and hmac.compare_digest(expected, token)
