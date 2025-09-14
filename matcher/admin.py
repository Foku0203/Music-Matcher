from django.contrib import admin
from .models import Artist, Album, Genre, Song, SongGenre

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "artist", "year")
    list_filter = ("year", "artist")

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "artist", "album")
    list_select_related = ("artist", "album")
    search_fields = ("title", "artist__name", "album__title")

@admin.register(SongGenre)
class SongGenreAdmin(admin.ModelAdmin):
    list_display = ("song", "genre")
    list_select_related = ("song", "genre")
