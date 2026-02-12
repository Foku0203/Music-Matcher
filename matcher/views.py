import os
import json
import numpy as np
import datetime
import cv2  # pip install opencv-python

from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # ✅ เพิ่มสำหรับการ Import
from django.conf import settings
from django.db.models import Q, Count
from django.db import transaction  # ✅ เพิ่มสำหรับการ Import

# --- TENSORFLOW ---
try:
    from tensorflow.keras.models import load_model
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠️ TensorFlow not installed.")

from .models import (
    User, UserScanLog, Song, Category, Interaction, Playlist, PlaylistItem,
    ModelVersion, ModelMetric, Recommendation, RetrainJob,
    Artist, Album  # ✅ เพิ่ม Artist และ Album เข้ามา
)
from .forms import CustomUserCreationForm, UserUpdateForm


# ==========================================
# 🧠 AI CONFIGURATION
# ==========================================
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

MODEL_PATH = os.path.join(settings.BASE_DIR, 'emotion_model_best.keras')
emotion_model = None

# สร้าง face cascade ไว้ครั้งเดียว
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

if TF_AVAILABLE and os.path.exists(MODEL_PATH):
    try:
        emotion_model = load_model(MODEL_PATH)
        print(f"✅ Loaded User Model: {MODEL_PATH}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
else:
    print(f"⚠️ Model not found at {MODEL_PATH}")


# ==========================================
# 🧩 HELPERS (PREPROCESS)
# ==========================================
def _imread_unicode(path: str):
    try:
        img = cv2.imread(path)
        if img is not None:
            return img
    except Exception:
        pass
    with open(path, "rb") as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return img

def preprocess_emotion_input(img_path, model, target_size=(48, 48)):
    # ... (Code ส่วนนี้เหมือนเดิมจากที่คุณมี แต่ผมย่อให้สั้นลงเพื่อความกระชับในคำตอบ) ...
    frame = _imread_unicode(img_path)
    if frame is None: raise ValueError("Image load failed")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
    
    if len(faces) > 0:
        x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
        margin = int(0.15 * max(w, h))
        x0, y0 = max(x - margin, 0), max(y - margin, 0)
        x1, y1 = min(x + w + margin, gray.shape[1]), min(y + h + margin, gray.shape[0])
        crop = gray[y0:y1, x0:x1]
    else:
        crop = gray

    crop = cv2.resize(crop, target_size, interpolation=cv2.INTER_AREA)
    crop = cv2.equalizeHist(crop) if crop.dtype == np.uint8 else crop
    crop_f = crop.astype("float32") / 255.0
    
    x_arr = np.expand_dims(crop_f, axis=-1) # (48,48,1)
    x_arr = np.expand_dims(x_arr, axis=0)   # (1,48,48,1)
    return x_arr, {}


# ==========================================
# 🆕 DATA IMPORT FUNCTION (เพิ่มส่วนนี้)
# ==========================================
@csrf_exempt
def import_songs_from_json(request):
    """
    ฟังก์ชันสำหรับ Import เพลงจากไฟล์ songdata.json เข้าสู่ Database
    รองรับโครงสร้าง Models ใหม่ (Artist, Album, Song)
    """
    if request.method == 'POST':
        try:
            # พยายามอ่านไฟล์จากที่วางไว้ในโปรเจกต์
            json_path = os.path.join(settings.BASE_DIR, 'songdata.json')
            
            if not os.path.exists(json_path):
                return JsonResponse({'status': 'error', 'message': 'File songdata.json not found in project root.'}, status=404)

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            created_count = 0
            updated_count = 0

            with transaction.atomic():
                for item in data:
                    # 1. จัดการ Artist
                    artist_name = item.get('artist', 'Unknown Artist')
                    artist, _ = Artist.objects.get_or_create(name=artist_name)

                    # 2. จัดการ Album
                    album_title = item.get('album')
                    album = None
                    if album_title:
                        album, _ = Album.objects.get_or_create(
                            title=album_title,
                            artist=artist
                        )

                    # 3. เตรียมข้อมูล
                    spotify_data = item.get('spotify', {}) or {}
                    audio_features = item.get('audio_features', {}) or {}
                    
                    release_date_str = item.get('release_date')
                    release_date = None
                    if release_date_str:
                        try:
                            release_date = datetime.datetime.strptime(release_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass

                    # 4. สร้าง/อัปเดต Song
                    song, created = Song.objects.update_or_create(
                        title=item.get('title'),
                        artist=artist,
                        defaults={
                            'album': album,
                            'release_date': release_date,
                            'lyrics': item.get('lyrics', ''),
                            'image_url': item.get('image_url', ''),
                            'genius_url': item.get('url', ''),
                            
                            # เก็บ Mood/Genre จาก JSON
                            'json_mood': item.get('mood', ''),
                            'json_genre': item.get('genre', ''),

                            # Spotify Info
                            'spotify_id': spotify_data.get('id'),
                            'spotify_link': spotify_data.get('link'),
                            'spotify_preview_url': spotify_data.get('preview_url'),
                            'spotify_embed_url': spotify_data.get('embed'),

                            # Audio Features
                            'valence': audio_features.get('valence', 0.5),
                            'energy': audio_features.get('energy', 0.5),
                            'tempo': audio_features.get('tempo', 120.0),
                            'danceability': audio_features.get('danceability', 0.5),
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

            return JsonResponse({
                'status': 'success',
                'message': f'✅ Import Complete! Created: {created_count}, Updated: {updated_count}'
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)


# ==========================================
# 🌐 PUBLIC & AUTH VIEWS
# ==========================================
def landing_view(request):
    if request.user.is_authenticated:
        return redirect('matcher:home')
    return render(request, 'matcher/landing.html')

@login_required(login_url='matcher:login')
def home_view(request):
    return render(request, 'matcher/landing.html', {'user': request.user})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if 'next' in request.GET:
                return redirect(request.GET.get('next'))
            if user.is_staff:
                return redirect('matcher:admin_panel')
            return redirect('matcher:landing')
        else:
            messages.error(request, "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    else:
        form = AuthenticationForm()
    return render(request, 'matcher/login.html', {'form': form})

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "ลงทะเบียนสำเร็จ!")
            return redirect('matcher:landing')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CustomUserCreationForm()
    return render(request, 'matcher/signup.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "ออกจากระบบแล้ว")
    return redirect('matcher:landing')


# ==========================================
# 📸 AI SCANNING
# ==========================================
@login_required(login_url='matcher:login')
def scan_view(request):
    if request.method == 'POST':
        image_file = request.FILES.get('image') or request.FILES.get('image_file')

        if not image_file:
            messages.error(request, "กรุณาเลือกรูปภาพ")
            return redirect('matcher:scan')

        try:
            scan_log = UserScanLog.objects.create(
                user=request.user,
                input_image=image_file,
                detected_emotion="Processing..."
            )

            detected_mood = "neutral"

            if emotion_model:
                img_path = scan_log.input_image.path
                # Preprocess
                x, meta = preprocess_emotion_input(img_path, emotion_model)
                
                # Predict
                prediction = emotion_model.predict(x, verbose=0)
                scores = prediction[0]
                max_index = int(np.argmax(scores))
                detected_mood = EMOTION_LABELS[max_index]

                print("✅ Prediction:", detected_mood)
            else:
                messages.warning(request, "AI Model not loaded.")

            scan_log.detected_emotion = detected_mood
            scan_log.save()

            return redirect('matcher:match_result', scan_id=scan_log.scan_id)

        except Exception as e:
            print(f"❌ Scan Error: {e}")
            messages.error(request, f"Error: {e}")
            return redirect('matcher:scan')

    return render(request, 'matcher/scan.html')


# ==========================================
# 🎵 MATCH RESULT (UPDATE)
# ==========================================
@login_required(login_url='matcher:login')
def match_result_view(request, scan_id):
    scan_log = get_object_or_404(UserScanLog, scan_id=scan_id, user=request.user)
    mood = (scan_log.detected_emotion or "neutral").lower()

    songs = Song.objects.none()
    try:
        # 1. Match แบบใหม่จากไฟล์ JSON (json_mood)
        songs = Song.objects.filter(json_mood__iexact=mood)

        # 2. ถ้าไม่เจอ ให้ Match แบบเก่า (SongEmotion Relationship)
        if not songs.exists():
            songs = Song.objects.filter(songemotion__emotion__name__iexact=mood)

        # 3. ถ้าไม่เจออีก ให้ดู Category แบบเก่า
        if not songs.exists():
            songs = Song.objects.filter(category__name__iexact=mood)

        # สุ่มผลลัพธ์
        songs = songs.order_by('?')[:5]
    except Exception as e:
        print(f"Error finding songs: {e}")

    # Fallback: ถ้าไม่เจอจริงๆ สุ่มเพลงอะไรก็ได้มาโชว์
    if not songs.exists():
        songs = Song.objects.order_by('?')[:10]

    main_song = songs[0] if songs.exists() else None

    context = {
        'scan_log': scan_log,
        'mood': mood,
        'songs': songs,
        'song': main_song,
        'user_image': scan_log.input_image.url
    }
    return render(request, 'matcher/match_result.html', context)


# ==========================================
# 🔎 SONG SEARCH API (UPDATE)
# ==========================================
@login_required(login_url='matcher:login')
def song_search_api(request):
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({"results": []})

    try:
        limit = int(request.GET.get('limit', 25))
    except ValueError:
        limit = 25
    limit = max(1, min(limit, 50))

    # ค้นหาทั้งชื่อเพลงและชื่อศิลปิน (รองรับ Model ใหม่ที่มี Artist)
    qs = (
        Song.objects
        .select_related('artist', 'album')
        .filter(Q(title__icontains=q) | Q(artist__name__icontains=q))
        .order_by('-song_id')
    )[:limit]

    results = []
    for s in qs:
        # ดึงข้อมูลแบบปลอดภัย
        artist_name = s.artist.name if s.artist else "Unknown"
        cover_url = s.image_url if s.image_url else (s.album.image_url if s.album else "")
        # ใช้ Preview URL จาก Spotify หรือ Genius URL
        link_url = s.spotify_preview_url or s.genius_url or ""

        results.append({
            "song_id": s.song_id,
            "title": s.title or "",
            "artist": artist_name,
            "cover_url": cover_url or "https://via.placeholder.com/50",
            "spotify_url": link_url,
        })

    return JsonResponse({"results": results})


# ==========================================
# 📊 USER DASHBOARD & HISTORY
# ==========================================
@login_required(login_url='matcher:login')
def dashboard_view(request):
    return render(request, 'matcher/dashboard.html', {'username': request.user.username})

@login_required(login_url='matcher:login')
def history_view(request):
    scan_history = UserScanLog.objects.filter(user=request.user).order_by('-created_at')[:10]
    playlist, _ = Playlist.objects.get_or_create(user=request.user, name="My Favorite Songs")
    saved_songs = PlaylistItem.objects.filter(playlist=playlist).select_related('song').order_by('-id')
    return render(request, 'matcher/history.html', {'saved_songs': saved_songs, 'scan_history': scan_history})

@login_required(login_url='matcher:login')
def profile(request):
    return render(request, 'matcher/profile.html')

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('matcher:history')
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'matcher/edit_profile.html', {'form': form})


# ==========================================
# ❤️ PLAYLIST & FEEDBACK
# ==========================================
@login_required(login_url='matcher:login')
@require_POST
def submit_feedback(request):
    song_id = request.POST.get('song_id')
    feedback_type = request.POST.get('type')

    if song_id and feedback_type:
        song = get_object_or_404(Song, song_id=song_id)
        Interaction.objects.update_or_create(
            user=request.user,
            song=song,
            defaults={'type': feedback_type, 'rating': 1 if feedback_type == 'like' else -1}
        )
        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error'}, status=400)

@login_required(login_url='matcher:login')
def add_to_playlist(request, song_id):
    song = get_object_or_404(Song, song_id=song_id)
    playlist, _ = Playlist.objects.get_or_create(user=request.user, name="My Favorite Songs")
    item, created = PlaylistItem.objects.get_or_create(playlist=playlist, song=song)
    if created:
        messages.success(request, f"Added '{song.title}' to favorites! ❤️")
    else:
        messages.info(request, f"'{song.title}' is already in your favorites.")
    return redirect(request.META.get('HTTP_REFERER', 'matcher:home'))


# ==========================================
# 🛠 ADMIN PANEL
# ==========================================
def is_admin(user):
    return user.is_authenticated and user.is_staff

def admin_login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                login(request, user)
                return redirect('matcher:admin_panel')
            else:
                messages.error(request, "Access Denied. Admins only.")
    form = AuthenticationForm()
    return render(request, 'matcher/admin_login.html', {'form': form})

@user_passes_test(is_admin, login_url='matcher:admin_login')
def admin_panel(request):
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    banned_users = User.objects.filter(is_active=False).count()
    last_week = timezone.now() - datetime.timedelta(days=7)
    new_users_count = User.objects.filter(date_joined__gte=last_week).count()
    
    try:
        most_liked_songs = Song.objects.annotate(
            like_count=Count('interaction', filter=Q(interaction__type='like'))
        ).order_by('-like_count')[:5]
    except Exception:
        most_liked_songs = Song.objects.all()[:5]
        
    recent_users = User.objects.order_by('-date_joined')[:5]
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'banned_users': banned_users,
        'new_users_count': new_users_count,
        'most_liked_songs': most_liked_songs,
        'recent_users': recent_users
    }
    return render(request, 'matcher/admin_panel.html', context)

@user_passes_test(is_admin, login_url='matcher:admin_login')
def user_management(request):
    users = User.objects.all().order_by('-date_joined')
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    last_week = timezone.now() - datetime.timedelta(days=7)
    new_users = users.filter(date_joined__gte=last_week).count()
    context = {
        'users': users,
        'total_users': total_users,
        'active_users': active_users,
        'new_users': new_users
    }
    return render(request, 'matcher/user_management.html', context)

@user_passes_test(is_admin, login_url='matcher:admin_login')
def behavior_analysis(request):
    return render(request, 'matcher/behavior_analysis.html')

@user_passes_test(is_admin, login_url='matcher:admin_login')
def song_database(request):
    query = request.GET.get('q', '')
    if query:
        songs = Song.objects.filter(
            Q(title__icontains=query) | Q(artist__name__icontains=query)
        ).order_by('-song_id')
    else:
        songs = Song.objects.all().order_by('-song_id')
    context = {'songs': songs, 'query': query}
    return render(request, 'matcher/song_database.html', context)

@user_passes_test(is_admin, login_url='matcher:admin_login')
def category_management(request):
    mood_categories = Category.objects.filter(type='MOOD').order_by('name')
    genre_categories = Category.objects.filter(type='GENRE').order_by('name')

    # นับจำนวนเพลง (รองรับทั้งแบบเก่าและใหม่)
    for c in mood_categories:
        count_old = Song.objects.filter(songemotion__emotion__name__iexact=c.name).distinct().count()
        count_new = Song.objects.filter(json_mood__iexact=c.name).count()
        c.display_count = max(count_old, count_new) # เลือกค่าที่มากกว่า

    for c in genre_categories:
        c.display_count = Song.objects.filter(category=c).count()

    context = {
        'mood_categories': mood_categories,
        'genre_categories': genre_categories,
    }
    return render(request, 'matcher/category_management.html', context)

@user_passes_test(is_admin, login_url='matcher:admin_login')
def category_songs(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    query = (request.GET.get('q') or '').strip()

    songs = Song.objects.select_related('artist', 'album')

    if category.type == 'GENRE':
        songs = songs.filter(category=category)

    elif category.type == 'MOOD':
        # ค้นหาทั้งแบบเก่า (SongEmotion) และแบบใหม่ (json_mood)
        songs = songs.filter(
            Q(songemotion__emotion__name__iexact=category.name) |
            Q(json_mood__iexact=category.name)
        ).distinct()

    else:
        songs = Song.objects.none()

    if query:
        songs = songs.filter(
            Q(title__icontains=query) |
            Q(artist__name__icontains=query)
        )

    songs = songs.order_by('-song_id')

    context = {
        'category': category,
        'songs': songs,
        'query': query,
    }
    return render(request, 'matcher/category_songs.html', context)

@user_passes_test(is_admin, login_url='matcher:admin_login')
def model_management(request):
    model_list = ModelVersion.objects.all().order_by('-created_at')
    active_model = ModelVersion.objects.filter(status='Active').first()
    active_metrics = {'accuracy': 92.5, 'loss': 0.15}

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'retrain':
            messages.success(request, "Retraining job started successfully!")
            return redirect('matcher:model_management')

    context = {
        'model_list': model_list,
        'active_model': active_model,
        'active_metrics': active_metrics
    }
    return render(request, 'matcher/model_management.html', context)