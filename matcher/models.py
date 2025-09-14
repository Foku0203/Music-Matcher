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

# ===================== EMOTIONS =====================

class Emotion(models.Model):
    name = models.CharField(max_length=30, unique=True)  # เช่น happy/sad/angry/calm/neutral

    class Meta:
        db_table = "emotions"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="idx_emotion_name"),
        ]

    def __str__(self):
        return self.name


class SongEmotion(models.Model):
    class Source(models.TextChoices):
        ML = "ml", "ML"
        RULE = "rule", "Rule"
        MANUAL = "manual", "Manual"

    song = models.ForeignKey("Song", on_delete=models.CASCADE, related_name="song_emotions")
    emotion = models.ForeignKey(Emotion, on_delete=models.CASCADE, related_name="emotion_songs")
    confidence = models.DecimalField(max_digits=4, decimal_places=3)  # 0..1
    source = models.CharField(max_length=20, choices=Source.choices)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "song_emotions"
        unique_together = (("song", "emotion"),)
        ordering = ["song_id", "emotion_id"]
        indexes = [
            models.Index(fields=["song"], name="idx_se_song"),
            models.Index(fields=["emotion"], name="idx_se_emotion"),
            models.Index(fields=["source"], name="idx_se_source"),
        ]

    def __str__(self):
        return f"{self.song.title} · {self.emotion.name} ({self.confidence})"
