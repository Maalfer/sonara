from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    date_joined: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    songs: Mapped[list["Song"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Song(Base):
    __tablename__ = "songs"
    __table_args__ = (UniqueConstraint("user_id", "youtube_id", name="unique_user_song"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(400))
    artist: Mapped[str] = mapped_column(String(400), default="Unknown Artist")
    youtube_url: Mapped[str] = mapped_column(String(600))
    youtube_id: Mapped[str] = mapped_column(String(32), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    thumbnail: Mapped[str] = mapped_column(String(600), default="")
    duration: Mapped[int] = mapped_column(Integer, default=0)
    plays: Mapped[int] = mapped_column(Integer, default=0)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="songs")
