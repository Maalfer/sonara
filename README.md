<div align="center">

<img src="static/images/logo.png" alt="Sonara" width="160" />

# Sonara

**Tu biblioteca de música personal.** Pega un enlace de YouTube, descarga el audio y reprodúcelo desde cualquier dispositivo.

![version](https://img.shields.io/badge/versi%C3%B3n-1.2.0-8a5cff)

[Características](#-características) · [Capturas](#-capturas) · [Despliegue](#-despliegue-con-docker) · [Configuración](#-configuración) · [Changelog](CHANGELOG.md)

</div>

---

## ✨ Características

- **Descarga automática** desde YouTube con [yt-dlp](https://github.com/yt-dlp/yt-dlp) + `ffmpeg` (audio MP3 192 kbps).
- **Biblioteca por usuario** con búsqueda, favoritos, ordenación y contadores de reproducciones.
- **Reproductor web** con cola, modo aleatorio, repetición, *seek* con soporte de `Range` HTTP y vista *now playing* a pantalla completa.
- **Panel de administración** para crear usuarios, asignar roles, banear y resetear contraseñas.
- **PWA instalable** con service worker que cachea el audio reproducido para uso offline.
- **Diseño oscuro, responsive**, sin dependencias de UI externas.

## 🛠 Stack

- **Backend:** Python 3.13 · [FastAPI](https://fastapi.tiangolo.com/) · SQLAlchemy 2.0 · gunicorn + worker de uvicorn
- **Frontend:** JavaScript vanilla · CSS nativo · plantillas Jinja2 · sin frameworks
- **Datos:** SQLite
- **Sesión/seguridad:** cookies de sesión firmadas (`itsdangerous`), hash de contraseñas PBKDF2-SHA256 (stdlib), CSRF por token de sesión
- **Multimedia:** yt-dlp · ffmpeg

## 📸 Capturas

<div align="center">

### 🎵 Biblioteca
Tu colección completa con búsqueda, favoritos, ordenación y vista lista/cuadrícula.

<img src="docs/screenshots/biblioteca.jpg" alt="Biblioteca" width="380" />

---

### ➕ Añadir desde YouTube
Pega uno o varios enlaces y la app extrae el audio automáticamente.

<img src="docs/screenshots/anadir-youtube.jpg" alt="Añadir desde YouTube" width="380" />

---

### 🎧 Now Playing
Vista a pantalla completa con controles, progreso y siguiente canción.

<img src="docs/screenshots/now-playing.jpg" alt="Now Playing" width="380" />

---

### 🛡 Panel de administración
Gestión de usuarios: crear, banear, cambiar rol y contraseña.

<img src="docs/screenshots/panel-admin.jpg" alt="Panel de administración" width="380" />

</div>

## 🚀 Despliegue con Docker

```bash
docker build -t sonara .

docker run -d --name sonara \
  -p 8000:8000 \
  -v sonara-data:/app/data \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e DEBUG=0 \
  -e ALLOWED_HOSTS=tu-dominio.com \
  sonara
```

Crea el primer administrador:

```bash
docker exec -it sonara python manage.py createsuperuser
```

## 🔧 Despliegue manual

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edita .env y define SECRET_KEY y ALLOWED_HOSTS

python manage.py initdb
python manage.py createsuperuser

gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Detrás de Nginx usa la configuración de `deploy/nginx.conf` como referencia (sirve `/static/` directamente desde `static_collected/`, una copia plana de la carpeta `static/`).

## ⚙ Configuración

Variables de entorno (ver [`.env.example`](.env.example)):

| Variable | Descripción |
| --- | --- |
| `SECRET_KEY` | Clave secreta para firmar las cookies de sesión (obligatoria en producción) |
| `DEBUG` | `1` para activar modo debug, `0` para producción |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma |
| `DB_PATH` | Ruta al archivo SQLite (opcional) |
| `MUSIC_UPLOADS_ROOT` | Carpeta donde se guardan los MP3 (opcional) |

## 📁 Estructura

```
.
├── app/
│   ├── main.py        # app FastAPI, middlewares, montaje de /static
│   ├── config.py       # configuración desde variables de entorno
│   ├── database.py     # engine SQLAlchemy y sesión por request
│   ├── models.py        # modelos User y Song
│   ├── security.py     # hash de contraseñas y tokens CSRF
│   ├── deps.py          # dependencias de autenticación (login/admin)
│   ├── flash.py          # mensajes flash de un solo uso en sesión
│   └── routers/
│       ├── accounts.py  # login, logout, panel admin de usuarios
│       └── music.py     # biblioteca, descarga yt-dlp, streaming
├── templates/           # plantillas Jinja2
├── static/
│   ├── css/              # estilos
│   ├── js/                # app + player
│   ├── icons/             # icon.svg (favicon vectorial)
│   └── images/            # logo.png y derivados (192/512, favicon, apple-touch)
├── docs/screenshots/      # capturas para el README
├── deploy/                # nginx.conf y unidad systemd de referencia
├── Dockerfile
├── manage.py              # CLI: initdb, createsuperuser
└── requirements.txt
```

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Maalfer/sonara&type=Date)](https://star-history.com/#Maalfer/sonara&Date)

## 📄 Licencia

MIT
