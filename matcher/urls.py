from django.urls import path
from . import views

app_name = "matcher"

urlpatterns = [
    path("", views.home, name="home"),
    path("song/<int:song_id>/", views.song_detail, name="song_detail"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-users/", views.admin_user_management, name="admin_user_management"),
    path("admin-behavior/", views.admin_behavior, name="admin_behavior"),
    path("admin-songs/", views.admin_song_database, name="admin_song_database"),
    path("admin-categories/", views.admin_category_management, name="admin_category_management"),
    path("admin-model/", views.admin_model, name="admin_model"),
]
    