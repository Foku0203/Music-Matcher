from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, UserProfile, Role, UserRole, UserSuspension,
    Artist, Album, Category, Song,
    Interaction, FavoriteSong, UserScanLog, PlayHistory,
    Playlist, PlaylistItem,
    ModelVersion, Recommendation, RetrainJob, TrainingLog
)

# ===================== INLINES =====================

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1

class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 1

# ===================== 1. USER MANAGEMENT ADMIN =====================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('id', 'username', 'email', 'status', 'age', 'gender', 'is_staff', 'is_active')
    list_display_links = ('id', 'username')
    list_filter = ('status', 'gender', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Info', {'fields': ('status', 'age', 'gender')}),
    )
    inlines = [UserProfileInline, UserRoleInline]

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_id', 'name')
    search_fields = ('name',)

@admin.register(UserSuspension)
class UserSuspensionAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)

# ===================== 2. CATALOG ADMIN =====================

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('artist_id', 'name', 'image_url')
    search_fields = ('name',)

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('album_id', 'title', 'artist', 'release_date')
    search_fields = ('title', 'artist__name')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'name', 'type')
    list_filter = ('type',)
    search_fields = ('name',)

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    # โชว์ข้อมูลตาม Model ใหม่
    list_display = ('song_id', 'title', 'artist', 'category', 'json_mood', 'valence', 'energy')
    list_filter = ('json_mood', 'category', 'created_at')
    search_fields = ('title', 'artist__name', 'album__title', 'json_mood')
    raw_id_fields = ('artist', 'album') 

# ===================== 3. USER ACTIVITY & OTHERS ADMIN =====================

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'song', 'type', 'rating', 'created_at')
    list_filter = ('type', 'created_at')

@admin.register(FavoriteSong)
class FavoriteSongAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'added_at')

@admin.register(PlayHistory)
class PlayHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'detected_emotion', 'source', 'started_at')
    list_filter = ('source', 'detected_emotion')

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'is_public', 'created_at')
    inlines = [PlaylistItemInline]

@admin.register(UserScanLog)
class UserScanLogAdmin(admin.ModelAdmin):
    list_display = ('scan_id', 'user', 'detected_emotion', 'created_at')
    readonly_fields = ('created_at',)

# ===================== 4. AI MODEL SYSTEM ADMIN =====================

@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    # ✅ แก้ไข: ลบ 'name' ออก ใส่ data_split, ndcg_score แทน
    list_display = ('id', 'version', 'algorithm', 'status', 'accuracy', 'ndcg_score', 'created_at')
    list_filter = ('status', 'algorithm')
    search_fields = ('version',)

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'song', 'context_emotion', 'score', 'generated_at')
    list_filter = ('context_emotion', 'algorithm')

@admin.register(RetrainJob)
class RetrainJobAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'model_version', 'status', 'started_at', 'completed_at')
    list_filter = ('status',)

@admin.register(TrainingLog)
class TrainingLogAdmin(admin.ModelAdmin):
    list_display = ('model_version', 'epoch_number', 'training_loss', 'validation_loss')
    list_filter = ('model_version',)