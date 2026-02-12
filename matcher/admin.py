from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import * # ===================== INLINES =====================

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

# ❌ ลบ SongEmotionInline และ SongGenreInline ออก 
# เพราะเราเปลี่ยนโครงสร้างไปเก็บใน Song โดยตรงแล้ว

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
    # โชว์ข้อมูลใหม่: json_mood, valence, energy
    list_display = ('song_id', 'title', 'artist', 'json_mood', 'valence', 'energy', 'spotify_id')
    list_filter = ('json_mood', 'created_at')
    search_fields = ('title', 'artist__name', 'album__title', 'spotify_id')
    
    # ❌ เอา inlines ออก เพราะไม่มี SongEmotion แล้ว
    inlines = []

# ===================== 3. USER ACTIVITY & OTHERS ADMIN =====================

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'song', 'type', 'rating', 'created_at')
    list_filter = ('type', 'created_at')

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')
    inlines = [PlaylistItemInline]

@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'version', 'algorithm', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'song', 'context_emotion', 'score', 'generated_at')
    list_filter = ('context_emotion', 'algorithm')

@admin.register(RetrainJob)
class RetrainJobAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'model_version', 'status', 'started_at')

@admin.register(UserScanLog)
class UserScanLogAdmin(admin.ModelAdmin):
    list_display = ('scan_id', 'user', 'detected_emotion', 'created_at')
    readonly_fields = ('created_at',)