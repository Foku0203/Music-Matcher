from django.urls import path
from . import views

app_name = "matcher"
urlpatterns = [
    path("", views.home, name="home"),
    path("songs/", views.song_list, name="song_list"),
    path("songs/<int:pk>/", views.song_detail, name="song_detail"),
    path("artists/<int:pk>/", views.artist_detail, name="artist_detail"),
    path("playlists/<int:pk>/", views.playlist_detail, name="playlist_detail"),
]
