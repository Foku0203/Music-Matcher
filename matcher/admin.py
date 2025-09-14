from django.contrib import admin
from .models import Artist, Album, Genre, Song, SongGenre, Emotion, SongEmotion

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["id", "name"]
    ordering = ["name"]

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "artist", "year"]
    list_filter = ["year", "artist"]
    search_fields = ["title", "artist__name"]

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["id", "name"]

class SongGenreInline(admin.TabularInline):
    model = SongGenre
    extra = 0

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "artist", "album"]
    list_filter = ["artist", "album"]
    search_fields = ["title", "artist__name", "album__title"]
    inlines = [SongGenreInline]

@admin.register(Emotion)
class EmotionAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["id", "name"]

@admin.register(SongEmotion)
class SongEmotionAdmin(admin.ModelAdmin):
    list_display = ["id", "song", "emotion", "confidence", "source", "updated_at"]
    list_filter = ["source", "emotion"]
    search_fields = ["song__title", "emotion__name"]
