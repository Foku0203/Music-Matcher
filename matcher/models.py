from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

# ===================== 1. USER MANAGEMENT =====================

class User(AbstractUser):
    # [แก้ Error admin.E108] เพิ่มฟิลด์ status ที่ Admin เรียกหา
    status = models.CharField(max_length=20, default='Active', help_text="User status (e.g., Active, Banned)")

class UserProfile(models.Model):
    # ใช้ settings.AUTH_USER_MODEL เพื่อลิงก์กับ User ตัวจริง
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.user.username

class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

class UserSuspension(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField()
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Suspension: {self.user.username}"

# ===================== 2. CATALOG (Artist / Song) =====================

class Artist(models.Model):
    artist_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    spotify_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

class Album(models.Model):
    album_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    release_year = models.IntegerField(null=True, blank=True)
    cover_url = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.title

class Song(models.Model):
    song_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True)
    platform = models.CharField(max_length=50, default='Spotify')
    external_id = models.CharField(max_length=255, null=True, blank=True)
    duration_sec = models.IntegerField(default=0, help_text="Duration in seconds")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    audio_features = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.title

class Genre(models.Model):
    genre_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class SongGenre(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)

class Emotion(models.Model):
    emotion_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class SongEmotion(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    emotion = models.ForeignKey(Emotion, on_delete=models.CASCADE)
    confidence = models.FloatField(default=0.0)
    source = models.CharField(max_length=50, default='AI')
    updated_at = models.DateTimeField(auto_now=True)

class EmotionScan(models.Model):
    scan_id = models.AutoField(primary_key=True)
    song = models.ForeignKey(Song, on_delete=models.CASCADE, null=True)
    scanned_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Pending')
    raw_data = models.TextField(null=True, blank=True)

# ===================== 3. USER ACTIVITY =====================

class Interaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    type = models.CharField(max_length=50)
    rating = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class FavoriteSong(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

class PlayHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    detected_emotion = models.CharField(max_length=50, null=True, blank=True)
    source = models.CharField(max_length=50, default='Web')
    started_at = models.DateTimeField(auto_now_add=True)
    duration_played = models.IntegerField(default=0)

class Playlist(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

# ===================== 4. AI / MLOPS =====================

class ModelVersion(models.Model):
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    algorithm = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} v{self.version}"

class Recommendation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    context_emotion = models.CharField(max_length=50)
    algorithm = models.CharField(max_length=100)
    score = models.FloatField()
    generated_at = models.DateTimeField(auto_now_add=True)

class RetrainJob(models.Model):
    job_id = models.AutoField(primary_key=True)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

class ModelMetric(models.Model):
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE)
    metric_name = models.CharField(max_length=100)
    value = models.FloatField()
    evaluated_at = models.DateTimeField(auto_now_add=True)