"""Sonara — biblioteca personal de música descargada de YouTube."""
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import Song

log = logging.getLogger(__name__)

YOUTUBE_DOMAINS = ("youtube.com", "youtu.be", "music.youtube.com")

SORT_FIELDS = {
    "recent": "-created_at",
    "oldest": "created_at",
    "title": "title",
    "artist": "artist",
    "plays": "-plays",
}


def _is_youtube_url(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return any(host == d or host.endswith(f".{d}") for d in YOUTUBE_DOMAINS)


def _serialize(song):
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "thumbnail": song.thumbnail,
        "duration": song.duration,
        "plays": song.plays,
        "is_favorite": song.is_favorite,
    }


@login_required
def index(request):
    songs = list(request.user.songs.all())
    return render(request, "music/index.html", {
        "songs_json": json.dumps([_serialize(s) for s in songs]),
    })


@login_required
@require_GET
def songs_list(request):
    q = (request.GET.get("search") or "").strip()
    sort = request.GET.get("sort") or "recent"
    favorites_only = request.GET.get("favorites") == "1"

    songs = request.user.songs.all()
    if q:
        songs = songs.filter(Q(title__icontains=q) | Q(artist__icontains=q))
    if favorites_only:
        songs = songs.filter(is_favorite=True)
    songs = songs.order_by(SORT_FIELDS.get(sort, "-created_at"))

    return JsonResponse({"songs": [_serialize(s) for s in songs]})


@login_required
@require_GET
def stream(request, song_id):
    song = get_object_or_404(Song, pk=song_id, user=request.user)
    try:
        return FileResponse(open(song.file_path, "rb"), content_type="audio/mpeg")
    except FileNotFoundError:
        raise Http404("Archivo no encontrado")


@login_required
@require_POST
def download(request):
    """Descarga audio de YouTube usando yt-dlp y lo añade a la biblioteca del usuario."""
    data = json.loads(request.body or "{}")
    url = (data.get("url") or "").strip()
    if not _is_youtube_url(url):
        return JsonResponse({"error": "URL de YouTube no válida"}, status=400)

    try:
        import yt_dlp
    except ImportError:
        return JsonResponse({"error": "yt-dlp no está instalado en el servidor"}, status=500)

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as probe:
            info = probe.extract_info(url, download=False)
    except Exception as exc:
        return JsonResponse({"error": f"No se pudo leer el vídeo: {exc}"}, status=400)

    yid = info.get("id")
    if not yid:
        return JsonResponse({"error": "No se pudo identificar el vídeo"}, status=400)
    if Song.objects.filter(user=request.user, youtube_id=yid).exists():
        return JsonResponse({"error": "Esta canción ya está en tu biblioteca"}, status=400)

    out_dir = settings.MUSIC_UPLOADS_ROOT / "songs"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{request.user.id}_{yid}"
    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out_dir / f"{stem}.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as exc:
        return JsonResponse({"error": f"Error al descargar: {exc}"}, status=500)

    song = Song.objects.create(
        user=request.user,
        title=info.get("title", "Unknown"),
        artist=info.get("uploader", "Unknown Artist"),
        youtube_url=url,
        youtube_id=yid,
        file_path=str(out_dir / f"{stem}.mp3"),
        thumbnail=info.get("thumbnail", ""),
        duration=info.get("duration") or 0,
    )
    return JsonResponse({"success": True, "song": _serialize(song)})


@login_required
@require_POST
def delete_song(request, song_id):
    song = get_object_or_404(Song, pk=song_id, user=request.user)
    try:
        Path(song.file_path).unlink(missing_ok=True)
    except OSError as exc:
        log.warning("delete_song: failed to unlink %s: %s", song.file_path, exc)
    song.delete()
    return JsonResponse({"success": True})


@login_required
@require_POST
def toggle_favorite(request, song_id):
    song = get_object_or_404(Song, pk=song_id, user=request.user)
    song.is_favorite = not song.is_favorite
    song.save(update_fields=["is_favorite"])
    return JsonResponse({"success": True, "is_favorite": song.is_favorite})


@login_required
@require_POST
def register_play(request, song_id):
    Song.objects.filter(pk=song_id, user=request.user).update(plays=F("plays") + 1)
    return JsonResponse({"success": True})


def service_worker(request):
    """Sirve sw.js desde la raíz (necesario para que su scope cubra todo el sitio)."""
    body = (settings.BASE_DIR / "static" / "sw.js").read_text(encoding="utf-8")
    resp = HttpResponse(body, content_type="application/javascript")
    resp["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp["Service-Worker-Allowed"] = "/"
    return resp
