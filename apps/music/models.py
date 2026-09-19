from django.conf import settings
from django.db import models


class Song(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="songs")
    title = models.CharField(max_length=400)
    artist = models.CharField(max_length=400, default="Unknown Artist", blank=True)
    youtube_url = models.URLField(max_length=600)
    youtube_id = models.CharField(max_length=32, db_index=True)
    file_path = models.CharField(max_length=500)
    thumbnail = models.URLField(max_length=600, blank=True, default="")
    duration = models.PositiveIntegerField(default=0, help_text="Duración en segundos")
    plays = models.PositiveIntegerField(default=0)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "youtube_id"), name="unique_user_song"),
        ]

    def __str__(self) -> str:
        return f"{self.artist} — {self.title}"
