from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import * # Import models ทั้งหมดของคุณ

# ===================== INLINES (ตัวช่วยแก้ไขข้อมูลลูก ในหน้าข้อมูลแม่) =====================

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1

class SongGenreInline(admin.TabularInline):
    model = SongGenre
    extra = 1

class SongEmotionInline(admin.TabularInline):
    model = SongEmotion
    extra = 1
    readonly_fields = ('updated_at',)

class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 1

# ===================== 1. USER MANAGEMENT ADMIN =====================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # 1. โชว์ UID (id) เป็นอันดับแรก
    list_display = ('id', 'username', 'email', 'status', 'age', 'gender', 'is_staff', 'is_active')
    list_display_links = ('id', 'username') # คลิกที่ ID หรือ Username เพื่อแก้ไข
    list_filter = ('status', 'gender', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    # เพิ่ม Field พิเศษที่คุณสร้างมาเข้าไปในหน้าแก้ไข
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Info', {'fields': ('status', 'age', 'gender')}),
    )
    # ใส่ Profile และ Role ให้แก้ได้ในหน้า User เลย
    inlines = [UserProfileInline, UserRoleInline]

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_id', 'name')
    search_fields = ('name',)

@admin.register(UserSuspension)
class UserSuspensionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'reason', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'reason')

# ===================== 2. CATALOG ADMIN =====================

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('artist_id', 'name', 'spotify_id')
    search_fields = ('name', 'spotify_id')

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('album_id', 'title', 'artist', 'release_year')
    list_filter = ('release_year',)
    search_fields = ('title', 'artist__name')

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('song_id', 'title', 'artist', 'album', 'duration_sec', 'platform', 'is_active')
    list_filter = ('is_active', 'platform', 'created_at')
    search_fields = ('title', 'artist__name', 'album__title', 'external_id')
    
    # แก้ไข Genre และ Emotion ได้เลยในหน้า Song ไม่ต้องไปหน้าแยก
    inlines = [SongGenreInline, SongEmotionInline]

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('genre_id', 'name')
    search_fields = ('name',)

@admin.register(Emotion)
class EmotionAdmin(admin.ModelAdmin):
    list_display = ('emotion_id', 'name')
    search_fields = ('name',)

@admin.register(EmotionScan)
class EmotionScanAdmin(admin.ModelAdmin):
    list_display = ('scan_id', 'song', 'status', 'scanned_at')
    list_filter = ('status', 'scanned_at')

# ===================== 3. USER ACTIVITY & OTHERS ADMIN =====================

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'song', 'type', 'rating', 'created_at')
    list_filter = ('type', 'created_at')

@admin.register(FavoriteSong)
class FavoriteSongAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'song', 'added_at')

@admin.register(PlayHistory)
class PlayHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'song', 'detected_emotion', 'source', 'started_at')
    list_filter = ('source', 'detected_emotion')

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'is_public', 'created_at')
    list_filter = ('is_public',)
    inlines = [PlaylistItemInline] # เพิ่มเพลงใน Playlist ได้เลย

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
    list_display = ('job_id', 'model_version', 'status', 'started_at', 'completed_at')

@admin.register(ModelMetric)
class ModelMetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'model_version', 'metric_name', 'value', 'evaluated_at')

@admin.register(UserScanLog)
class UserScanLogAdmin(admin.ModelAdmin):
    list_display = ('scan_id', 'user', 'detected_emotion', 'created_at')
    readonly_fields = ('created_at',) 
    # รูปภาพจะโชว์เป็น link ให้คลิกดูได้ในหน้าแก้ไข