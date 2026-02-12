from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

# ===================== 1. USER MANAGEMENT =====================

class User(AbstractUser):
    status = models.CharField(max_length=20, default='Active')
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other'), ('LG', 'LGBTQ+')], null=True, blank=True)

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    province = models.CharField(max_length=100, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

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

class UserSuspension(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField()
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

# ===================== 2. CATALOG & MUSIC (ปรับปรุงใหม่) =====================

class Artist(models.Model):
    artist_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    image_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.name

class Album(models.Model):
    album_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    release_date = models.DateField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.title

# ✅ Category: ใช้แทน Genre และ Emotion เดิม
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50) 
    type = models.CharField(max_length=20, choices=[('MOOD', 'Mood'), ('GENRE', 'Genre')])

    def __str__(self):
        return f"{self.name} ({self.type})"

class Song(models.Model):
    song_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True)
    
    # --- ข้อมูลทั่วไป ---
    release_date = models.DateField(null=True, blank=True)
    lyrics = models.TextField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    genius_url = models.URLField(null=True, blank=True)
    
    # --- Mood & Genre (จาก JSON) ---
    json_mood = models.CharField(max_length=50, null=True, blank=True) 
    json_genre = models.CharField(max_length=100, null=True, blank=True)
    
    # Optional: ถ้าอยากเชื่อมกับ Category ด้วย (เผื่ออนาคต)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    # --- Spotify Data ---
    spotify_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    spotify_link = models.URLField(null=True, blank=True)
    spotify_preview_url = models.URLField(null=True, blank=True)
    spotify_embed_url = models.URLField(null=True, blank=True)

    # --- Audio Features ---
    valence = models.FloatField(default=0.5)
    energy = models.FloatField(default=0.5)
    tempo = models.FloatField(default=120.0)
    danceability = models.FloatField(default=0.5)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.artist.name}"

# ===================== 3. USER ACTIVITY =====================

class Interaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=[('like', 'Like'), ('dislike', 'Dislike'), ('skip', 'Skip')])
    rating = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class FavoriteSong(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

class UserScanLog(models.Model):
    scan_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    input_image = models.ImageField(upload_to='scan_uploads/')
    detected_emotion = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PlayHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    detected_emotion = models.CharField(max_length=50, null=True)
    source = models.CharField(max_length=50, default='manual') 
    started_at = models.DateTimeField(auto_now_add=True)

# ===================== 4. PLAYLIST =====================

class Playlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

# ===================== 5. AI MODEL SYSTEM =====================

class ModelVersion(models.Model):
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    algorithm = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

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
    metric_name = models.CharField(max_length=50)
    value = models.FloatField()
    evaluated_at = models.DateTimeField(auto_now_add=True)