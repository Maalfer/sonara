import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Song",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=400)),
                ("artist", models.CharField(blank=True, default="Unknown Artist", max_length=400)),
                ("youtube_url", models.URLField(max_length=600)),
                ("youtube_id", models.CharField(db_index=True, max_length=32)),
                ("file_path", models.CharField(max_length=500)),
                ("thumbnail", models.URLField(blank=True, default="", max_length=600)),
                ("duration", models.PositiveIntegerField(default=0, help_text="Duración en segundos")),
                ("plays", models.PositiveIntegerField(default=0)),
                ("is_favorite", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="songs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="song",
            constraint=models.UniqueConstraint(fields=("user", "youtube_id"), name="unique_user_song"),
        ),
    ]
