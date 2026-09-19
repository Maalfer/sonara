from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/songs", views.songs_list, name="songs_list"),
    path("api/songs/download", views.download, name="download"),
    path("api/songs/<int:song_id>/delete", views.delete_song, name="delete_song"),
    path("api/songs/<int:song_id>/favorite", views.toggle_favorite, name="toggle_favorite"),
    path("api/songs/<int:song_id>/play", views.register_play, name="register_play"),
    path("api/stream/<int:song_id>", views.stream, name="stream"),
]
