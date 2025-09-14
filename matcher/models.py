from django.db import models

class Artist(models.Model):
    name = models.CharField(max_length=200, unique=True)
    def __str__(self): return self.name

class Album(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="albums")
    title = models.CharField(max_length=200)
    year = models.IntegerField(null=True, blank=True)
    class Meta: unique_together = ("artist", "title")
    def __str__(self): return f"{self.title} ({self.artist.name})"

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Song(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="songs")
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, related_name="songs")
    genres = models.ManyToManyField(Genre, through="SongGenre", related_name="songs")
    class Meta: unique_together = ("title", "artist", "album")
    def __str__(self): return self.title

class SongGenre(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)
    class Meta: unique_together = ("song", "genre")
    def __str__(self): return f"{self.song.title} - {self.genre.name}"
