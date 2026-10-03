import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..deps import require_csrf_header, require_user_api, require_user_page
from ..models import Song, User
from ..security import ensure_csrf

log = logging.getLogger(__name__)
router = APIRouter()

YOUTUBE_DOMAINS = ("youtube.com", "youtu.be", "music.youtube.com")

SORT_FIELDS = {
    "recent": ("created_at", True),
    "oldest": ("created_at", False),
    "title": ("title", False),
    "artist": ("artist", False),
    "plays": ("plays", True),
}


def _is_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return any(host == d or host.endswith(f".{d}") for d in YOUTUBE_DOMAINS)


def _serialize(song: Song) -> dict:
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "album": song.album,
        "thumbnail": song.thumbnail,
        "duration": song.duration,
        "plays": song.plays,
        "is_favorite": song.is_favorite,
    }


def _templates(request: Request):
    return request.app.state.templates


@router.get("/", name="index")
def index(request: Request, user: User = Depends(require_user_page), db: Session = Depends(get_db)):
    songs = db.scalars(select(Song).where(Song.user_id == user.id)).all()
    csrf_token = ensure_csrf(request)
    return _templates(request).TemplateResponse(
        request,
        "music/index.html",
        {
            "user": user,
            "songs_json": json.dumps([_serialize(s) for s in songs]),
            "csrf_token": csrf_token,
            "version": config.VERSION,
        },
    )


@router.get("/api/songs", name="songs_list")
def songs_list(
    request: Request,
    search: str = "",
    sort: str = "recent",
    favorites: str = "",
    artist: str = "",
    album: str = "",
    user: User = Depends(require_user_api),
    db: Session = Depends(get_db),
):
    q = (search or "").strip()
    field_name, descending = SORT_FIELDS.get(sort, SORT_FIELDS["recent"])

    stmt = select(Song).where(Song.user_id == user.id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Song.title.ilike(like), Song.artist.ilike(like)))
    if favorites == "1":
        stmt = stmt.where(Song.is_favorite.is_(True))
    if artist:
        stmt = stmt.where(Song.artist == artist)
    if album:
        stmt = stmt.where(Song.album == album)

    column = getattr(Song, field_name)
    stmt = stmt.order_by(column.desc() if descending else column.asc())

    songs = db.scalars(stmt).all()
    return JSONResponse({"songs": [_serialize(s) for s in songs]})


def _group_user_songs(db: Session, user: User, key_fn, skip_empty_key: bool = False) -> list[dict]:
    """Agrupa las canciones del usuario por la clave que devuelva key_fn (artista o álbum)."""
    songs = db.scalars(
        select(Song).where(Song.user_id == user.id).order_by(Song.created_at.desc())
    ).all()
    groups: dict[str, dict] = {}
    for s in songs:
        key = key_fn(s)
        if skip_empty_key and not key:
            continue
        key = key or "Desconocido"
        g = groups.setdefault(key, {"name": key, "count": 0, "thumbnail": ""})
        g["count"] += 1
        if not g["thumbnail"] and s.thumbnail:
            g["thumbnail"] = s.thumbnail
    return sorted(groups.values(), key=lambda g: g["name"].lower())


@router.get("/api/artists", name="artists_list")
def artists_list(user: User = Depends(require_user_api), db: Session = Depends(get_db)):
    artists = _group_user_songs(db, user, lambda s: s.artist)
    return JSONResponse({"artists": artists})


@router.get("/api/albums", name="albums_list")
def albums_list(user: User = Depends(require_user_api), db: Session = Depends(get_db)):
    albums = _group_user_songs(db, user, lambda s: s.album, skip_empty_key=True)
    return JSONResponse({"albums": albums})


class DownloadRequest(BaseModel):
    url: str = ""


RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


@router.get("/api/stream/{song_id}", name="stream")
def stream(
    song_id: int,
    request: Request,
    user: User = Depends(require_user_api),
    db: Session = Depends(get_db),
):
    song = db.scalar(select(Song).where(Song.id == song_id, Song.user_id == user.id))
    if song is None:
        return JSONResponse({"error": "No encontrada"}, status_code=404)

    path = Path(song.file_path)
    if not path.exists():
        return JSONResponse({"error": "Archivo no encontrado"}, status_code=404)

    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        match = RANGE_RE.match(range_header)
        if match:
            start_s, end_s = match.groups()
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else file_size - 1
            end = min(end, file_size - 1)
            if start > end or start >= file_size:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})
            length = end - start + 1
            with open(path, "rb") as f:
                f.seek(start)
                data = f.read(length)
            return Response(
                content=data,
                status_code=206,
                media_type="audio/mpeg",
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(length),
                },
            )

    with open(path, "rb") as f:
        data = f.read()
    return Response(
        content=data,
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
    )


@router.post("/api/songs/download", name="download", dependencies=[Depends(require_csrf_header)])
def download(
    request: Request,
    payload: DownloadRequest,
    user: User = Depends(require_user_api),
    db: Session = Depends(get_db),
):
    url = (payload.url or "").strip()
    if not _is_youtube_url(url):
        return JSONResponse({"error": "URL de YouTube no válida"}, status_code=400)

    try:
        import yt_dlp
    except ImportError:
        return JSONResponse({"error": "yt-dlp no está instalado en el servidor"}, status_code=500)

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as probe:
            info = probe.extract_info(url, download=False)
    except Exception as exc:
        return JSONResponse({"error": f"No se pudo leer el vídeo: {exc}"}, status_code=400)

    yid = info.get("id")
    if not yid:
        return JSONResponse({"error": "No se pudo identificar el vídeo"}, status_code=400)
    existing = db.scalar(select(Song).where(Song.user_id == user.id, Song.youtube_id == yid))
    if existing is not None:
        return JSONResponse({"error": "Esta canción ya está en tu biblioteca"}, status_code=400)

    out_dir = config.MUSIC_UPLOADS_ROOT / "songs"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{user.id}_{yid}"
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
        return JSONResponse({"error": f"Error al descargar: {exc}"}, status_code=500)

    song = Song(
        user_id=user.id,
        title=info.get("title", "Unknown"),
        artist=info.get("uploader", "Unknown Artist"),
        album=info.get("album") or "",
        youtube_url=url,
        youtube_id=yid,
        file_path=str(out_dir / f"{stem}.mp3"),
        thumbnail=info.get("thumbnail", ""),
        duration=info.get("duration") or 0,
    )
    db.add(song)
    db.commit()
    db.refresh(song)
    return JSONResponse({"success": True, "song": _serialize(song)})


@router.post("/api/songs/{song_id}/delete", name="delete_song", dependencies=[Depends(require_csrf_header)])
def delete_song(
    song_id: int,
    user: User = Depends(require_user_api),
    db: Session = Depends(get_db),
):
    song = db.scalar(select(Song).where(Song.id == song_id, Song.user_id == user.id))
    if song is None:
        return JSONResponse({"error": "No encontrada"}, status_code=404)
    try:
        Path(song.file_path).unlink(missing_ok=True)
    except OSError as exc:
        log.warning("delete_song: failed to unlink %s: %s", song.file_path, exc)
    db.delete(song)
    db.commit()
    return JSONResponse({"success": True})


@router.post("/api/songs/{song_id}/favorite", name="toggle_favorite", dependencies=[Depends(require_csrf_header)])
def toggle_favorite(
    song_id: int,
    user: User = Depends(require_user_api),
    db: Session = Depends(get_db),
):
    song = db.scalar(select(Song).where(Song.id == song_id, Song.user_id == user.id))
    if song is None:
        return JSONResponse({"error": "No encontrada"}, status_code=404)
    song.is_favorite = not song.is_favorite
    db.commit()
    return JSONResponse({"success": True, "is_favorite": song.is_favorite})


@router.post("/api/songs/{song_id}/play", name="register_play", dependencies=[Depends(require_csrf_header)])
def register_play(
    song_id: int,
    user: User = Depends(require_user_api),
    db: Session = Depends(get_db),
):
    song = db.scalar(select(Song).where(Song.id == song_id, Song.user_id == user.id))
    if song is not None:
        song.plays += 1
        db.commit()
    return JSONResponse({"success": True})
