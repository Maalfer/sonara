from django.urls import path

from . import views

urlpatterns = [
    path("panel/", views.panel, name="panel"),
    path("panel/create", views.create_user, name="panel_create_user"),
    path("panel/<int:user_id>/role", views.toggle_role, name="panel_toggle_role"),
    path("panel/<int:user_id>/ban", views.toggle_ban, name="panel_toggle_ban"),
    path("panel/<int:user_id>/password", views.set_password, name="panel_set_password"),
    path("panel/<int:user_id>/delete", views.delete_user, name="panel_delete_user"),
]
