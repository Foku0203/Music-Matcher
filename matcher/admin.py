from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Role, UserRole, UserSuspension, UserProfile, # เพิ่ม UserProfile ตรงนี้
    Artist, Album, Song, Genre, SongGenre,
    Emotion, SongEmotion, EmotionScan,
    Interaction, FavoriteSong, PlayHistory,
    Playlist, PlaylistItem,
    ModelVersion, Recommendation, RetrainJob, ModelMetric
)

# =============================================================================
# 1. USER MANAGEMENT (จัดการผู้ใช้)
# =============================================================================

# สร้าง Inline เพื่อโชว์ Age, Gender, Province ในหน้า User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Additional Info (Age/Gender/Province)'

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "status", "is_staff", "date_joined")
    list_filter = ("status", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
    
    # เพิ่มส่วน Custom Info ในหน้าแก้ไข User
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Info', {'fields': ('status',)}),
    )
    
    # เพิ่ม Inline Profile เข้าไป
    inlines = [UserProfileInline]

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_id", "name")

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "assigned_at")
    list_filter = ("role",)
    search_fields = ("user__username",)

@admin.register(UserSuspension)
class UserSuspensionAdmin(admin.ModelAdmin):
    list_display = ("user", "reason", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "start_date")
    search_fields = ("user__username", "reason")

# =============================================================================
# 2. CATALOG (จัดการเพลงและศิลปิน)
# =============================================================================

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("artist_id", "name", "spotify_id")
    search_fields = ("name",)

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("album_id", "title", "artist", "release_year")
    list_filter = ("release_year", "artist")
    search_fields = ("title", "artist__name")

# --- จัดการ Genre และ Emotion ภายในหน้า Song (Inline) ---
class SongGenreInline(admin.TabularInline):
    model = SongGenre
    extra = 1

class SongEmotionInline(admin.TabularInline):
    model = SongEmotion
    extra = 1

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    # ใช้ฟิลด์ที่มีจริงใน model ใหม่
    list_display = ("song_id", "title", "artist", "album", "platform", "is_active") 
    list_filter = ("platform", "is_active", "artist")
    search_fields = ("title", "artist__name", "external_id")
    
    # ใช้ Inlines แทนฟิลด์ genres เดิม
    inlines = [SongGenreInline, SongEmotionInline] 

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("genre_id", "name")

@admin.register(Emotion)
class EmotionAdmin(admin.ModelAdmin):
    list_display = ("emotion_id", "name")

@admin.register(SongEmotion)
class SongEmotionAdmin(admin.ModelAdmin):
    list_display = ("song", "emotion", "confidence", "source", "updated_at")
    list_filter = ("source", "emotion")

@admin.register(EmotionScan)
class EmotionScanAdmin(admin.ModelAdmin):
    list_display = ("scan_id", "song", "scanned_at", "status")
    list_filter = ("status",)

# =============================================================================
# 3. USER ACTIVITY & PLAYLISTS (กิจกรรมผู้ใช้)
# =============================================================================

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ("user", "song", "type", "rating", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("user__username", "song__title")

@admin.register(FavoriteSong)
class FavoriteSongAdmin(admin.ModelAdmin):
    list_display = ("user", "song", "added_at")
    search_fields = ("user__username", "song__title")

@admin.register(PlayHistory)
class PlayHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "song", "detected_emotion", "started_at", "duration_played")
    list_filter = ("detected_emotion", "source")
    search_fields = ("user__username", "song__title")

class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 1

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_public", "created_at")
    list_filter = ("is_public",)
    search_fields = ("name", "user__username")
    inlines = [PlaylistItemInline]

# =============================================================================
# 4. MLOPS & RECOMMENDER (ระบบ AI)
# =============================================================================

@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "algorithm", "status", "created_at")
    list_filter = ("status", "algorithm")
    search_fields = ("name", "version")

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("user", "context_emotion", "algorithm", "generated_at")
    list_filter = ("algorithm", "context_emotion")
    search_fields = ("user__username",)

@admin.register(RetrainJob)
class RetrainJobAdmin(admin.ModelAdmin):
    list_display = ("job_id", "model_version", "status", "started_at", "completed_at")
    list_filter = ("status",)

@admin.register(ModelMetric)
class ModelMetricAdmin(admin.ModelAdmin):
    list_display = ("model_version", "metric_name", "value", "evaluated_at")
    list_filter = ("metric_name",)