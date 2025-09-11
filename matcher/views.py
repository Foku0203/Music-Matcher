from django.shortcuts import render, get_object_or_404
from .models import Song, Artist, Genre, Playlist

def home(request):
    songs = Song.objects.select_related("artist","album").order_by("title")[:12]
    artists = Artist.objects.order_by("name")[:10]
    genres = Genre.objects.order_by("name")[:12]
    return render(request, "matcher/home.html", {"songs": songs, "artists": artists, "genres": genres})

def song_list(request):
    qs = Song.objects.select_related("artist","album").order_by("title")
    genre = request.GET.get("genre")
    if genre:
        qs = qs.filter(songgenre__genre__name__iexact=genre)
    emotion = request.GET.get("emotion")
    if emotion:
        qs = qs.filter(emotion_scores__emotion__name__iexact=emotion).distinct()
    return render(request, "matcher/song_list.html", {"songs": qs})

def song_detail(request, pk: int):
    song = get_object_or_404(Song, pk=pk)
    return render(request, "matcher/song_detail.html", {"song": song})

def artist_detail(request, pk: int):
    artist = get_object_or_404(Artist, pk=pk)
    return render(request, "matcher/artist_detail.html", {"artist": artist})

def playlist_detail(request, pk: int):
    playlist = get_object_or_404(Playlist, pk=pk)
    return render(request, "matcher/playlist_detail.html", {"playlist": playlist})
