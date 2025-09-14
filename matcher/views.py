from django.shortcuts import render
from .models import Song

def home(request):
    songs = Song.objects.all()
    return render(request, 'matcher/home.html', {'songs': songs})

def song_detail(request, song_id):
    song = Song.objects.get(pk=song_id)
    return render(request, 'matcher/song_detail.html', {'song': song})