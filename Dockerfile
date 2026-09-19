FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/uploads/songs /app/static_collected \
 && python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 sonara \
 && chown -R sonara:sonara /app
USER sonara

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--threads", "4", \
     "--worker-class", "gthread", \
     "--timeout", "180", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
