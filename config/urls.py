from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as account_views
from apps.music import views as music_views

urlpatterns = [
    path("login/", account_views.login_view, name="login"),
    path("logout/", account_views.logout_view, name="logout"),
    path("", include("apps.accounts.urls")),
    path("sw.js", music_views.service_worker, name="sw"),
    path("django-admin/", admin.site.urls),
    path("", include("apps.music.urls")),
]
