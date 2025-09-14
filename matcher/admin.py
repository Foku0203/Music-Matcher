from django.contrib import admin
from .models import (
    Artist, Album, Song, Genre, SongGenre,  # ลบ Emotion ออกจากที่นี่
    SongEmotion, EmotionScan, Interaction, FavoriteSong, PlayHistory,
    Playlist, PlaylistItem,
    ModelVersion, Recommendation, RecommendationItem,
    RetrainJob, AdminAction, ModelMetric, ModelAction, ModelDeployment
)

admin.site.register([
    Artist, Album, Song, Genre, SongGenre,  # ลบ Emotion ออกจากที่นี่
    SongEmotion, EmotionScan, Interaction, FavoriteSong, PlayHistory,
    Playlist, PlaylistItem, ModelVersion, Recommendation, RecommendationItem,
    RetrainJob, AdminAction, ModelMetric, ModelAction, ModelDeployment
])