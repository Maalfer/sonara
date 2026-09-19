from django.contrib import admin

from .models import Song


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "user", "duration", "plays", "is_favorite", "created_at")
    list_filter = ("user", "is_favorite")
    search_fields = ("title", "artist", "youtube_id")
