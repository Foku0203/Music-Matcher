from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import URLValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import uuid

# ===================== ARTISTS / ALBUMS / GENRES =====================

class Artist(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Album(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="albums")
    title = models.CharField(max_length=200)
    year = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("artist", "title")

    def __str__(self):
        return f"{self.title} ({self.artist.name})"


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Song(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="songs")
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, related_name="songs")
    genres = models.ManyToManyField(Genre, through="SongGenre", related_name="songs")

    slug = models.SlugField(unique=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # วินาที
    LANGUAGE_CHOICES = [
        ("th", "Thai"),
        ("en", "English"),
    ]
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="th")
    release_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)  # soft delete

    class Meta:
        unique_together = ("title", "artist")
        indexes = [
            models.Index(fields=["title"], name="idx_song_title"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.artist.name}-{self.title}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class SongGenre(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("song", "genre")

    def __str__(self):
        return f"{self.song.title} - {self.genre.name}"


# ===================== EMOTIONS =====================

class Emotion(models.Model):
    name = models.CharField(max_length=30, unique=True)

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
    confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=1.000,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
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


# ===================== USERS =====================

class AppUser(AbstractUser):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=20,
        choices=[("active", "active"), ("suspended", "suspended")],
        default="active",
    )
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)  # soft delete
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"], name="idx_users_email"),
            models.Index(fields=["username"], name="idx_users_username"),
            models.Index(fields=["status"], name="idx_users_status"),
        ]

    def __str__(self):
        return f"{self.username} <{self.email}>"


# ===================== USER BEHAVIOR =====================

class UserBehavior(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="behaviors")
    detected_emotion = models.ForeignKey(Emotion, on_delete=models.SET_NULL, null=True, blank=True)
    recommended_song = models.ForeignKey(Song, on_delete=models.SET_NULL, null=True, blank=True, related_name="recommended_to")
    clicked_song = models.ForeignKey(Song, on_delete=models.SET_NULL, null=True, blank=True, related_name="clicked_by")
    feedback = models.CharField(
        max_length=20,
        choices=[("like", "like"), ("dislike", "dislike"), ("skip", "skip")],
        null=True,
        blank=True,
    )
    session_id = models.UUIDField(default=uuid.uuid4)
    device_info = models.CharField(max_length=200, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_behaviors"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ip_address"], name="idx_behavior_ip"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.detected_emotion} - {self.recommended_song}"


# ===================== PLAYLISTS =====================

class Playlist(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="playlists")
    name = models.CharField(max_length=100)
    songs = models.ManyToManyField(Song, related_name="in_playlists")
    is_public = models.BooleanField(default=False)
    mood_tag = models.ForeignKey(Emotion, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "playlists"

    def __str__(self):
        return f"{self.name} ({self.user.username})"


# ===================== SONG LINKS =====================

def validate_platform_url(value, platform):
    if platform == "youtube" and "youtube.com" not in value:
        raise ValidationError("URL ต้องเป็น YouTube เท่านั้น")
    if platform == "spotify" and "spotify.com" not in value:
        raise ValidationError("URL ต้องเป็น Spotify เท่านั้น")


class SongLink(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="links")
    platform = models.CharField(
        max_length=20,
        choices=[("youtube", "YouTube"), ("spotify", "Spotify")]
    )
    url = models.URLField(validators=[URLValidator()])
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        validate_platform_url(self.url, self.platform)
        super().save(*args, **kwargs)

    class Meta:
        db_table = "song_links"
        unique_together = ("song", "platform")

    def __str__(self):
        return f"{self.song.title} [{self.platform}]"


# ===================== ADMIN ACTIVITY =====================

class AdminActivity(models.Model):
    admin = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="admin_activities")
    action = models.CharField(max_length=50)  # เช่น add_song, delete_user
    detail = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=200, null=True, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_activities"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action"], name="idx_admin_action"),
        ]

    def __str__(self):
        return f"{self.admin.username} - {self.action}"
