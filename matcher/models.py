from django.db import models
from django.utils import timezone
from django.conf import settings

User = settings.AUTH_USER_MODEL


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


# ---------- Catalog ----------
class Artist(TimeStampedModel):
    name = models.CharField(max_length=255)
    class Meta:
        db_table = "artists"
        ordering = ["name"]
    def __str__(self):
        return self.name


class Album(TimeStampedModel):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="albums")
    title = models.CharField(max_length=255)
    release_year = models.IntegerField(null=True, blank=True)
    cover_url = models.TextField(blank=True)
    class Meta:
        db_table = "albums"
        ordering = ["title"]
    def __str__(self):
        return f"{self.title} — {self.artist.name}"


class Song(TimeStampedModel):
    class Platform(models.TextChoices):
        YOUTUBE = "youtube", "youtube"
        SPOTIFY = "spotify", "spotify"

    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="songs")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="songs")
    title = models.CharField(max_length=255)
    duration_sec = models.IntegerField(default=0)
    platform = models.CharField(max_length=20, choices=Platform.choices, default=Platform.YOUTUBE)
    external_id = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    lyrics = models.CharField(max_length=1000, blank=True)

    class Meta:
        db_table = "songs"
        ordering = ["title"]

    def __str__(self):
        return self.title


class Genre(TimeStampedModel):
    name = models.CharField(max_length=60, unique=True, db_index=True)
    class Meta:
        db_table = "genres"
        ordering = ["name"]
    def __str__(self):
        return self.name


class SongGenre(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)
    class Meta:
        db_table = "song_genres"
        unique_together = ("song", "genre")


class Emotion(TimeStampedModel):
    name = models.CharField(max_length=30)
    class Meta:
        db_table = "emotions"
        ordering = ["name"]
    def __str__(self):
        return self.name


class SongEmotion(TimeStampedModel):
    class Source(models.TextChoices):
        ML = "ml", "ml"
        RULE = "rule", "rule"
        MANUAL = "manual", "manual"

    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="emotion_scores")
    emotion = models.ForeignKey(Emotion, on_delete=models.CASCADE)
    confidence = models.DecimalField(max_digits=4, decimal_places=3)  # 0..1.xxx
    source = models.CharField(max_length=20, choices=Source.choices)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "song_emotions"
        unique_together = ("song", "emotion", "source")


class EmotionScan(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emotion_scans")
    emotion = models.ForeignKey(Emotion, on_delete=models.CASCADE)
    method = models.CharField(max_length=20, default="manual")
    confidence = models.DecimalField(max_digits=4, decimal_places=3, default=1)
    created_at = models.DateTimeField(default=timezone.now)
    class Meta:
        db_table = "emotion_scans"


# ---------- User activity ----------
class Interaction(TimeStampedModel):
    class Type(models.TextChoices):
        LIKE = "like", "like"
        DISLIKE = "dislike", "dislike"
        FAVORITE = "favorite", "favorite"
        RATE = "rate", "rate"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="interactions")
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="interactions")
    type = models.CharField(max_length=12, choices=Type.choices)
    rating = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "interactions"
        unique_together = ("user", "song", "type")


class FavoriteSong(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_songs")
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="fav_by")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "favorite_songs"
        unique_together = ("user", "song")


class PlayHistory(TimeStampedModel):
    class Source(models.TextChoices):
        MANUAL = "manual", "manual"
        NONE = "none", "none"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="play_history")
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="play_history")
    detected_emotion = models.ForeignKey(Emotion, on_delete=models.SET_NULL, null=True, blank=True)
    scan = models.ForeignKey(EmotionScan, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.NONE)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "play_history"


class Playlist(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="playlists")
    name = models.CharField(max_length=255)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "playlists"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class PlaylistItem(TimeStampedModel):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="items")
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    position = models.IntegerField(default=0)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "playlist_items"
        unique_together = ("playlist", "song")
        ordering = ["position"]


# ---------- Recommender ----------
class ModelVersion(TimeStampedModel):
    class Status(models.TextChoices):
        READY = "ready", "ready"
        DEPRECATED = "deprecated", "deprecated"

    name = models.CharField(max_length=60)
    version = models.CharField(max_length=40)
    algorithm = models.CharField(max_length=60, blank=True)
    artifact_uri = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.READY)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "model_versions"


class Recommendation(TimeStampedModel):
    class Algo(models.TextChoices):
        CF = "cf", "cf"
        CB = "cb", "cb"
        HYBRID = "hybrid", "hybrid"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recommendations")
    context_emotion = models.ForeignKey(Emotion, on_delete=models.SET_NULL, null=True, blank=True)
    algorithm = models.CharField(max_length=40, choices=Algo.choices, default=Algo.CF)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.SET_NULL, null=True, blank=True)
    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "recommendations"


class RecommendationItem(models.Model):
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name="items")
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    rank = models.IntegerField()
    score = models.DecimalField(max_digits=6, decimal_places=3)

    class Meta:
        db_table = "recommendation_items"
        unique_together = ("recommendation", "song")


class RetrainJob(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "queued"
        RUNNING = "running", "running"
        FAILED = "failed", "failed"
        SUCCEEDED = "succeeded", "succeeded"

    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    target_model = models.CharField(max_length=60)  # emotion-cnn|rec-cf
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    output_model_version = models.ForeignKey(ModelVersion, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "retrain_jobs"


class AdminAction(TimeStampedModel):
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=40)  # suspend_user|edit_song|retrain
    target_type = models.CharField(max_length=30)
    target_id = models.BigIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "admin_actions"


class ModelMetric(TimeStampedModel):
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name="metrics")
    dataset_name = models.CharField(max_length=60)   # train|val|test
    accuracy = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    val_accuracy = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    loss = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    ndcg_at_10 = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    recall_at_10 = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    mrr = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "model_metrics"


class ModelAction(TimeStampedModel):
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name="actions")
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=20)  # promote|rollback|export
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "model_actions"


class ModelDeployment(TimeStampedModel):
    class Stage(models.TextChoices):
        PRODUCTION = "production", "production"
        STAGING = "staging", "staging"

    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name="deployments")
    stage = models.CharField(max_length=20, choices=Stage.choices)
    is_active = models.BooleanField(default=True)
    deployed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    deployed_at = models.DateTimeField(default=timezone.now)
    rolled_back_from = models.ForeignKey(ModelVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name="rolled_back_to")

    class Meta:
        db_table = "model_deployments"
