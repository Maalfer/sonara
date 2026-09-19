# Sonara

Tu biblioteca de música personal. Pega un enlace de YouTube, descarga el audio y reprodúcelo desde cualquier dispositivo.

![Sonara](static/icons/icon.svg)

## Características

- Descarga automática de audio desde YouTube (vía `yt-dlp`)
- Biblioteca por usuario con búsqueda, favoritos y ordenación
- Reproductor web con cola, aleatorio, repetición y modo "now playing"
- Panel de administración para gestionar usuarios
- PWA instalable con service worker
- Diseño oscuro, responsive, sin dependencias de UI externas

## Stack

- Python 3.13 · Django 5.1
- SQLite · WhiteNoise
- gunicorn · yt-dlp · ffmpeg

## Despliegue con Docker

```bash
docker build -t sonara .
docker run -d --name sonara \
  -p 8000:8000 \
  -v sonara-data:/app/data \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e DEBUG=0 \
  -e ALLOWED_HOSTS=tu-dominio.com \
  -e CSRF_TRUSTED_ORIGINS=https://tu-dominio.com \
  sonara
```

Crea el primer usuario administrador:

```bash
docker exec -it sonara python manage.py createsuperuser
```

## Despliegue manual

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edita .env y define SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Detrás de Nginx usa la configuración de `deploy/nginx.conf` como referencia.

## Configuración

Variables de entorno (ver `.env.example`):

| Variable | Descripción |
| --- | --- |
| `SECRET_KEY` | Clave secreta de Django (obligatoria en producción) |
| `DEBUG` | `1` para activar modo debug, `0` para producción |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma |
| `CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS de confianza para CSRF |
| `DB_PATH` | Ruta al archivo SQLite (opcional) |
| `MUSIC_UPLOADS_ROOT` | Carpeta donde se guardan los MP3 (opcional) |

## Estructura

```
.
├── apps/
│   ├── accounts/    # login, logout, panel admin de usuarios
│   └── music/       # modelos, descarga yt-dlp, streaming
├── config/          # settings, urls, wsgi
├── templates/       # Django templates
├── static/          # CSS, JS, iconos, manifest, service worker
├── deploy/          # nginx.conf y unidad systemd de referencia
├── Dockerfile
├── manage.py
└── requirements.txt
```

## Licencia

MIT
