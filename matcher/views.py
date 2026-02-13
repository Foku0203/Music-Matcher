import os
import json
import numpy as np
import datetime
import cv2  # pip install opencv-python
from django.core.paginator import Paginator
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Q, Count, Avg
from django.db import transaction
from .models import *
from .forms import CustomUserCreationForm, UserUpdateForm
from django.core.files.storage import FileSystemStorage

# --- TENSORFLOW ---
try:
    from tensorflow.keras.models import load_model
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠️ TensorFlow not installed.")




# ==========================================
# 🧠 AI CONFIGURATION & DYNAMIC LOADER
# ==========================================
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

# สร้าง face cascade ไว้ครั้งเดียว
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# ตัวแปร Global สำหรับเก็บสถานะโมเดล
CURRENT_MODEL_NAME = 'emotion_model_best.keras' # ตั้งค่าเริ่มต้นให้เป็นตัวนี้
MODEL_PATH = os.path.join(settings.BASE_DIR, CURRENT_MODEL_NAME)
emotion_model = None

def load_ai_model(model_filename):
    """ ฟังก์ชันสำหรับโหลดหรือสลับโมเดล AI """
    global emotion_model, MODEL_PATH, CURRENT_MODEL_NAME
    
    CURRENT_MODEL_NAME = model_filename
    MODEL_PATH = os.path.join(settings.BASE_DIR, model_filename)
    
    if TF_AVAILABLE and os.path.exists(MODEL_PATH):
        try:
            emotion_model = load_model(MODEL_PATH)
            print(f"✅ โหลดโมเดลสำเร็จ: {CURRENT_MODEL_NAME}")
            return True, f"Switched to {CURRENT_MODEL_NAME} successfully!"
        except Exception as e:
            print(f"❌ โหลดโมเดลไม่สำเร็จ: {e}")
            return False, f"Error loading model: {e}"
    else:
        print(f"⚠️ ไม่พบไฟล์โมเดลที่: {MODEL_PATH}")
        return False, f"Model file '{model_filename}' not found in BASE_DIR."

# เรียกใช้งานครั้งแรกตอนรัน python manage.py runserver
load_ai_model(CURRENT_MODEL_NAME)


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
# 🆕 DATA IMPORT FUNCTION
# ==========================================
@csrf_exempt
def import_songs_from_json(request):
    if request.method == 'POST':
        try:
            json_path = os.path.join(settings.BASE_DIR, 'songdata.json')
            
            if not os.path.exists(json_path):
                return JsonResponse({'status': 'error', 'message': 'File songdata.json not found.'}, status=404)

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            created_count = 0
            updated_count = 0

            with transaction.atomic():
                for item in data:
                    artist_name = item.get('artist', 'Unknown Artist')
                    artist, _ = Artist.objects.get_or_create(name=artist_name)

                    album_title = item.get('album')
                    album = None
                    if album_title:
                        album, _ = Album.objects.get_or_create(
                            title=album_title,
                            artist=artist
                        )

                    spotify_data = item.get('spotify', {}) or {}
                    audio_features = item.get('audio_features', {}) or {}
                    
                    release_date_str = item.get('release_date')
                    release_date = None
                    if release_date_str:
                        try:
                            release_date = datetime.datetime.strptime(release_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass

                    song, created = Song.objects.update_or_create(
                        title=item.get('title'),
                        artist=artist,
                        defaults={
                            'album': album,
                            'release_date': release_date,
                            'lyrics': item.get('lyrics', ''),
                            'image_url': item.get('image_url', ''),
                            'genius_url': item.get('url', ''),
                            
                            'json_mood': item.get('mood', ''),
                            'json_genre': item.get('genre', ''),

                            'spotify_id': spotify_data.get('id'),
                            'spotify_link': spotify_data.get('link'),

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
                x, meta = preprocess_emotion_input(img_path, emotion_model)
                
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
# 🎵 MATCH RESULT
# ==========================================
# views.py

@login_required(login_url='matcher:login')
def match_result_view(request, scan_id):
    # 1. ดึงข้อมูล Scan Log ของ User
    scan_log = get_object_or_404(UserScanLog, scan_id=scan_id, user=request.user)
    
    # 2. รับค่าอารมณ์ใบหน้า (1 ใน 7 อารมณ์)
    # ถ้ามีการกดเลือก Mood ใหม่จากหน้าเว็บ (?mood=...) ให้ใช้ค่านั้น 
    # ถ้าไม่มี ให้ใช้ค่าที่ AI ทายได้จาก database
    face_emotion = (scan_log.detected_emotion or "neutral").lower()
    selected_emotion = request.GET.get('mood', face_emotion).lower()

    # =========================================================
    # 🎯 LOGIC: จับคู่ 7 อารมณ์ (Face) -> 4 อารมณ์เพลง (Music)
    # =========================================================
    emotion_mapping = {
        # Face Emotion  ->  Music Mood (ใน Database เพลง)
        'angry':            'Angry',
        'disgust':          'Angry',   # รังเกียจ -> เพลงหนักๆ/ระบายอารมณ์
        'fear':             'Relax',   # กลัว -> เพลงผ่อนคลาย (หรือจะใช้ Sad ก็ได้แล้วแต่ชอบ)
        'happy':            'Happy',
        'sad':              'Sad',
        'surprise':         'Happy',   # ตกใจ/ตื่นเต้น -> เพลงสนุก
        'neutral':          'Relax'    # เฉยๆ -> เพลงชิลๆ
    }

    # แปลงเป็น Music Mood (ถ้าหาไม่เจอให้ Default เป็น Relax)
    target_music_mood = emotion_mapping.get(selected_emotion, 'Relax')

    # =========================================================
    # 🎵 QUERY: ค้นหาเพลงจาก json_mood ที่แปลงแล้ว
    # =========================================================
    songs = Song.objects.none()
    try:
        # ค้นหาเพลงที่เป็น 'Angry', 'Happy', 'Sad', หรือ 'Relax'
        songs = Song.objects.filter(json_mood__icontains=target_music_mood)
        
        # ถ้าหาไม่เจอ ให้ลองหาจาก Category
        if not songs.exists():
            songs = Song.objects.filter(category__name__icontains=target_music_mood)
            
        # สุ่มเพลงมา 10 เพลง
        songs = songs.order_by('?')[:10]
        
    except Exception as e:
        print(f"Error finding songs: {e}")

    # Fallback: ถ้ายังหาไม่เจอเลยจริงๆ ให้เอาเพลงทั้งหมดมาสุ่ม
    if not songs.exists():
        songs = Song.objects.all().order_by('?')[:10]

    main_song = songs[0] if songs.exists() else None

    # ==================================================
    # ✅ Interaction Data (ดึงข้อมูล Like/Favorite)
    # ==================================================
    interaction_likes = set(Interaction.objects.filter(user=request.user, type='like').values_list('song_id', flat=True))
    favorite_likes = set(FavoriteSong.objects.filter(user=request.user).values_list('song_id', flat=True))
    liked_song_ids = list(interaction_likes.union(favorite_likes))

    context = {
        'scan_log': scan_log,
        
        # 'mood' ส่งค่า 1 ใน 7 (selected_emotion) ไปเพื่อให้หน้าเว็บแสดงผล Highlight ปุ่มถูกอัน
        'mood': selected_emotion,  
        
        # ส่งค่า Music Mood ไปด้วยเผื่ออยากโชว์ว่า "กำลังแนะนำเพลงแนว Relax"
        'music_mood': target_music_mood, 

        'songs': songs,
        'song': main_song,
        'user_image': scan_log.input_image.url if scan_log.input_image else None,
        'liked_song_ids': liked_song_ids
    }
    return render(request, 'matcher/match_result.html', context)

# ==========================================
# 🔎 BROWSE & SEARCH API
# ==========================================
@login_required(login_url='matcher:login')
def browse_view(request):
    songs = Song.objects.all().order_by('-song_id')[:100]
    
    # ✅ ดึง ID เพลงที่ชอบจาก Interaction และ FavoriteSong
    interaction_likes = set(Interaction.objects.filter(user=request.user, type='like').values_list('song_id', flat=True))
    favorite_likes = set(FavoriteSong.objects.filter(user=request.user).values_list('song_id', flat=True))
    liked_song_ids = list(interaction_likes.union(favorite_likes))

    return render(request, 'matcher/browsesong.html', {
        'songs': songs,
        'liked_song_ids': liked_song_ids
    })

@login_required(login_url='matcher:login')
def song_search_api(request):
    q = (request.GET.get('q') or '').strip()
    mood_filter = (request.GET.get('mood') or '').strip().lower()
    
    try:
        limit = int(request.GET.get('limit', 50))
    except ValueError:
        limit = 50

    qs = Song.objects.select_related('artist', 'album')

    if mood_filter:
        qs = qs.filter(json_mood__iexact=mood_filter)

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(artist__name__icontains=q))

    qs = qs.order_by('-song_id')[:limit]

    # ✅ ดึง ID เพลงที่ชอบ
    interaction_likes = set(Interaction.objects.filter(user=request.user, type='like').values_list('song_id', flat=True))
    favorite_likes = set(FavoriteSong.objects.filter(user=request.user).values_list('song_id', flat=True))
    liked_ids_set = interaction_likes.union(favorite_likes)

    results = []
    for s in qs:
        artist_name = s.artist.name if s.artist else "Unknown"
        cover_url = s.image_url if s.image_url else (s.album.image_url if s.album else "")
        link_url = s.spotify_link or s.genius_url or ""

        results.append({
            "song_id": s.song_id,
            "title": s.title or "",
            "artist": artist_name,
            "cover_url": cover_url or "https://via.placeholder.com/50",
            "spotify_url": link_url,
            "json_mood": s.json_mood or "",
            "is_liked": s.song_id in liked_ids_set,
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
    
    # ดึงเพลงจาก FavoriteSong เพื่อแสดงในหน้า Liked Songs
    saved_songs_qs = FavoriteSong.objects.filter(user=request.user).select_related('song').order_by('-added_at')
    
    # แปลงโครงสร้างให้เหมือน PlaylistItem เดิม
    saved_songs = []
    for fav in saved_songs_qs:
        saved_songs.append({'song': fav.song, 'added_at': fav.added_at})

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
        # ✅ บันทึกลง Interaction
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
    
    # ✅ 1. บันทึกลง FavoriteSong
    fav_item, created = FavoriteSong.objects.get_or_create(user=request.user, song=song)
    
    # ✅ 2. บันทึกลง Interaction
    Interaction.objects.update_or_create(
        user=request.user, 
        song=song, 
        defaults={'type': 'like', 'rating': 1}
    )

    # ✅ 3. เก็บลง Playlist เดิม
    playlist, _ = Playlist.objects.get_or_create(user=request.user, name="My Favorite Songs")
    PlaylistItem.objects.get_or_create(playlist=playlist, song=song)

    if created:
        messages.success(request, f"Added '{song.title}' to favorites! ❤️")
    else:
        messages.info(request, f"'{song.title}' is already in your favorites.")
        
    return redirect(request.META.get('HTTP_REFERER', 'matcher:home'))

@login_required
def toggle_favorite(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    # ค้นหาว่า user นี้ชอบเพลงนี้ไหม
    favorite = FavoriteSong.objects.filter(user=request.user, song=song)
    
    if favorite.exists():
        favorite.delete() # ถ้าเจอ ให้ลบทิ้ง (Unlike)
        
    return redirect('matcher:history')


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
            like_count=Count('favoritesong') 
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
    
    # คำนวณ New User (ใน 30 วันที่ผ่านมา)
    last_month_date = timezone.now() - datetime.timedelta(days=30)
    new_users = users.filter(date_joined__gte=last_month_date).count()

    # เปรียบเทียบกับเดือนที่แล้ว
    prev_month_date = timezone.now() - datetime.timedelta(days=60)
    total_last_month = User.objects.filter(date_joined__lt=last_month_date).count()
    
    growth_total = 0
    if total_last_month > 0:
        growth_total = ((total_users - total_last_month) / total_last_month) * 100

    context = {
        'users': users,
        'total_users': total_users,
        'active_users': active_users,
        'new_users': new_users,
        'growth_total': round(growth_total, 1),
    }
    return render(request, 'matcher/user_management.html', context)

# ==========================================
# 📊 BEHAVIOR ANALYSIS (Fixed & Added)
# ==========================================
@user_passes_test(is_admin, login_url='matcher:admin_login')
def behavior_analysis(request):
    users = User.objects.all()
    total_users = users.count()

    # 1. Age Analytics
    avg_age_data = users.aggregate(Avg('age'))
    avg_age = round(avg_age_data['age__avg']) if avg_age_data['age__avg'] else 0

    # 2. Gender Ratio (Model uses M, F, O)
    male_count = users.filter(gender='M').count()
    female_count = users.filter(gender='F').count()
    other_count = total_users - (male_count + female_count)

    if total_users > 0:
        male_percent = round((male_count / total_users) * 100, 1)
        female_percent = round((female_count / total_users) * 100, 1)
        other_percent = round((other_count / total_users) * 100, 1)
    else:
        male_percent = female_percent = other_percent = 0

    # 3. Top Genre Overall (Based on Likes)
    top_genre_qs = Interaction.objects.filter(type='like') \
        .values('song__json_genre') \
        .annotate(total_likes=Count('id')) \
        .order_by('-total_likes')
    
    global_top_genre = top_genre_qs[0]['song__json_genre'] if top_genre_qs.exists() else "No Data"

    # 4. Total Interactions
    total_interactions = Interaction.objects.count()

    # 5. User Specific Data
    user_data_list = []
    for u in users:
        # Find favorite genre per user
        user_fav_genre = Interaction.objects.filter(user=u, type='like') \
            .values('song__json_genre') \
            .annotate(c=Count('id')) \
            .order_by('-c').first()
        
        user_top_genre = user_fav_genre['song__json_genre'] if user_fav_genre else None

        user_data_list.append({
            'user': u,
            'top_genre': user_top_genre
        })

    context = {
        'avg_age': avg_age,
        'male_percent': male_percent,
        'female_percent': female_percent,
        'other_percent': other_percent,
        'top_genre': global_top_genre,
        'total_interactions': total_interactions,
        'user_data': user_data_list,
    }
    # หมายเหตุ: ชื่อ Template ต้องตรงกับไฟล์ HTML ที่คุณมี
    return render(request, 'matcher/behavior_analysis.html', context)


# ฟังก์ชันเปลี่ยนสถานะ (ระงับ/อนุมัติ)
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, "ไม่สามารถระงับตัวเองได้")
    else:
        user.is_active = not user.is_active
        user.save()
        status_msg = "อนุมัติ" if user.is_active else "ระงับ"
        messages.success(request, f"จัดการผู้ใช้ {user.username} ({status_msg}) เรียบร้อย")
    return redirect('matcher:user_management')

# ฟังก์ชันลบผู้ใช้
@user_passes_test(is_admin)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_staff:
        messages.error(request, "ไม่สามารถลบ Admin ได้")
    else:
        user.delete()
        messages.success(request, "ลบผู้ใช้เรียบร้อยแล้ว")
    return redirect('matcher:user_management')

# matcher/views.py

from django.core.paginator import Paginator # 1. อย่าลืม import นี้ด้านบนสุดไฟล์

@user_passes_test(is_admin, login_url='matcher:login')
def song_database(request):
    query = request.GET.get('q', '')
    genre = request.GET.get('genre')
    mood = request.GET.get('mood')

    # ดึงเพลงทั้งหมด
    songs_list = Song.objects.all().select_related('artist', 'album').order_by('-song_id')

    # กรองข้อมูล (ถ้ามี)
    if query:
        songs_list = songs_list.filter(
            Q(title__icontains=query) | 
            Q(artist__name__icontains=query) | 
            Q(album__title__icontains=query)
        )
    if genre:
        songs_list = songs_list.filter(json_genre__icontains=genre)
    if mood:
        songs_list = songs_list.filter(json_mood__icontains=mood)

    # 2. 🔥 จุดสำคัญ: ต้องทำ Pagination ก่อนส่งไปหน้าเว็บ
    paginator = Paginator(songs_list, 50)  # แบ่งทีละ 50 เพลง
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number) # ได้เป็น Page Object (มี start_index)

    # ข้อมูลสำหรับ Dropdown ตัวกรอง (ถ้าหน้า Admin คุณมี)
    all_genres = Song.objects.values_list('json_genre', flat=True).distinct()
    all_moods = Song.objects.values_list('json_mood', flat=True).distinct()

    context = {
        'songs': page_obj,  # ✅ ต้องส่ง page_obj (ไม่ใช่ songs_list)
        'query': query,
        'selected_genre': genre,
        'selected_mood': mood,
        'all_genres': sorted(filter(None, set(all_genres))),
        'all_moods': sorted(filter(None, set(all_moods))),
    }
    
    return render(request, 'matcher/song_database.html', context)

@require_POST
@user_passes_test(is_admin)
def save_song(request):
    # 1. รับค่าจาก Form
    song_id = request.POST.get('song_id')
    title = request.POST.get('title')
    artist_name = request.POST.get('artist')
    album_title = request.POST.get('album')
    json_genre = request.POST.get('json_genre')
    json_mood = request.POST.get('json_mood')
    image_url = request.POST.get('image_url') # ✅ รับค่า URL รูปภาพ
    
    # 2. จัดการ Artist (หาที่มีอยู่ หรือสร้างใหม่)
    artist, _ = Artist.objects.get_or_create(name=artist_name.strip())
    
    # 3. จัดการ Album (ถ้ามี)
    album = None
    if album_title:
        album, created = Album.objects.get_or_create(title=album_title.strip(), artist=artist)
        
        # ถ้ามีการอัปโหลดรูปปกอัลบั้ม (แบบไฟล์) ก็บันทึกด้วย
        if 'cover_image' in request.FILES:
            album.cover_url = request.FILES['cover_image'] 
            album.save()

    # 4. บันทึกข้อมูล Song
    if song_id: 
        # === EDIT (แก้ไข) ===
        song = get_object_or_404(Song, song_id=song_id)
        song.title = title
        song.artist = artist
        song.album = album
        song.json_genre = json_genre
        song.json_mood = json_mood
        song.image_url = image_url # ✅ บันทึก image_url
        song.save()
        messages.success(request, f"Updated song: {title}")
    else: 
        # === ADD (เพิ่มใหม่) ===
        Song.objects.create(
            title=title,
            artist=artist,
            album=album,
            json_genre=json_genre,
            json_mood=json_mood,
            image_url=image_url # ✅ บันทึก image_url
        )
        messages.success(request, f"Added new song: {title}")

    return redirect('matcher:song_database')

@user_passes_test(is_admin)
def delete_song(request, song_id):
    song = get_object_or_404(Song, song_id=song_id)
    title = song.title
    song.delete()
    messages.success(request, f"Deleted song: {title}")
    return redirect('matcher:song_database')

def category_management(request):
    # แยกประเภทหมวดหมู่
    moods = Category.objects.filter(type='MOOD')
    genres = Category.objects.filter(type='GENRE')

    # ฟังก์ชันช่วยนับจำนวนเพลง (Count Songs)
    # เนื่องจาก Song เก็บเป็น json_mood/json_genre เราจะค้นหาจาก text
    for m in moods:
        m.display_count = Song.objects.filter(json_mood__icontains=m.name).count()
    
    for g in genres:
        g.display_count = Song.objects.filter(json_genre__icontains=g.name).count()

    context = {
        'mood_categories': moods,
        'genre_categories': genres,
        'total_moods': moods.count(),
        'total_genres': genres.count()
    }
    return render(request, 'matcher/category_management.html', context)

def save_category(request):
    if request.method == "POST":
        cat_id = request.POST.get('category_id')
        name = request.POST.get('name')
        cat_type = request.POST.get('type')

        if cat_id: # Edit
            category = get_object_or_404(Category, pk=cat_id)
            category.name = name
            category.type = cat_type
            category.save()
        else: # Create
            Category.objects.create(name=name, type=cat_type)
            
    return redirect('matcher:category_management')

def delete_category(request, cat_id):
    category = get_object_or_404(Category, pk=cat_id)
    category.delete()
    return redirect('matcher:category_management')

# (Optional) หน้าดูเพลงในหมวดนั้นๆ
def category_songs(request, cat_id):
    category = get_object_or_404(Category, pk=cat_id)
    if category.type == 'MOOD':
        songs = Song.objects.filter(json_mood__icontains=category.name)
    else:
        songs = Song.objects.filter(json_genre__icontains=category.name)
        
    return render(request, 'matcher/song_database.html', {'songs': songs, 'query': category.name})

def category_management(request):
    # ดึงข้อมูลแยกประเภท
    moods = Category.objects.filter(type='MOOD').order_by('name')
    genres = Category.objects.filter(type='GENRE').order_by('name')

    # --- ส่วนนับจำนวนเพลง (Count Songs) ---
    # ระบบจะค้นหาว่ามีเพลงไหนที่มีคำว่าชื่อ Category อยู่ใน json_mood หรือ json_genre บ้าง
    for m in moods:
        m.display_count = Song.objects.filter(json_mood__icontains=m.name).count()
    
    for g in genres:
        g.display_count = Song.objects.filter(json_genre__icontains=g.name).count()

    context = {
        'mood_categories': moods,
        'genre_categories': genres,
    }
    return render(request, 'matcher/category_management.html', context)

# ==========================================
# 2. ฟังก์ชันบันทึก (Add / Edit)
# ==========================================
def save_category(request):
    if request.method == "POST":
        cat_id = request.POST.get('category_id') # รับ ID จาก Hidden Input ใน Modal
        name = request.POST.get('name')
        cat_type = request.POST.get('type')

        if cat_id: 
            # กรณีแก้ไข (Edit)
            category = get_object_or_404(Category, pk=cat_id)
            category.name = name
            category.type = cat_type
            category.save()
            messages.success(request, f"Updated category: {name}")
        else: 
            # กรณีสร้างใหม่ (Add New)
            Category.objects.create(name=name, type=cat_type)
            messages.success(request, f"Created new category: {name}")
            
    return redirect('matcher:category_management')

# ==========================================
# 3. ฟังก์ชันลบ (Delete)
# ==========================================
def delete_song(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    title = song.title
    song.delete()
    messages.success(request, f"Deleted song: {title}")
    return redirect('matcher:song_database')

# ==========================================
# 4. ฟังก์ชันกดดูเพลงในหมวดนั้น (View Songs)
# ==========================================
def category_songs(request, cat_id):
    category = get_object_or_404(Category, pk=cat_id)
    
    # กรองเพลงตามประเภทของ Category
    if category.type == 'MOOD':
        # หาเพลงที่มีชื่อ Mood นี้อยู่ใน field json_mood
        songs_list = Song.objects.filter(json_mood__icontains=category.name)
    else:
        # หาเพลงที่มีชื่อ Genre นี้อยู่ใน field json_genre
        songs_list = Song.objects.filter(json_genre__icontains=category.name)

    # ใช้ Pagination เหมือนหน้า Song Database ปกติ (50 เพลงต่อหน้า)
    paginator = Paginator(songs_list, 50)
    page_number = request.GET.get('page')
    songs = paginator.get_page(page_number)

    # ส่งไปที่หน้า song_database.html โดยระบุ Query เพื่อให้หน้าแสดงผลว่ากำลังดูหมวดไหน
    context = {
        'songs': songs,
        'query': f"Category: {category.name}", # แสดงหัวข้อการค้นหา
        'selected_genre': category.name if category.type == 'GENRE' else '',
        'selected_mood': category.name if category.type == 'MOOD' else '',
    }
    return render(request, 'matcher/song_database.html', context)


@login_required
def record_interaction(request, song_id, action_type):
    # action_type จะเป็น 'like' หรือ 'dislike'
    song = get_object_or_404(Song, pk=song_id)
    
    # เช็คว่ามี interaction เดิมอยู่ไหม
    interaction = Interaction.objects.filter(user=request.user, song=song).first()

    if interaction:
        if interaction.type == action_type:
            # ถ้ากดซ้ำ (เช่น ชอบอยู่แล้ว กดชอบอีกที) -> ให้ลบออก (Un-like/Un-dislike)
            interaction.delete()
            current_action = 'none'
        else:
            # ถ้าเปลี่ยนใจ (เช่น จาก Dislike -> Like) -> ให้อัปเดต
            interaction.type = action_type
            interaction.save()
            current_action = action_type
    else:
        # ถ้าไม่เคยกดมาก่อน -> สร้างใหม่
        Interaction.objects.create(user=request.user, song=song, type=action_type)
        current_action = action_type

    # ส่งค่ากลับไปบอกหน้าเว็บว่าสถานะตอนนี้คืออะไร
    return JsonResponse({'status': 'ok', 'action': current_action})


# ========================================== #
# ==========================================
# 🧠 AI MODEL MANAGEMENT VIEWS
# ==========================================

@user_passes_test(is_admin, login_url='matcher:admin_login')
def model_management(request):
    """
    ฟังก์ชันหลักสำหรับแสดงหน้า AI Model
    รวบรวมข้อมูลทั้งจาก Directory (ไฟล์ .keras) และ Database (ประวัติการ Training)
    """
    # --- 1. ส่วนอ่านไฟล์ Model จากเครื่อง (สำหรับโชว์ในตาราง) ---
    model_files = []
    for file in os.listdir(settings.BASE_DIR):
        if file.endswith('.keras') or file.endswith('.h5'):
            file_path = os.path.join(settings.BASE_DIR, file)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            model_files.append({
                'filename': file,
                'size': f"~{size_mb:.1f} MB"
            })

    # --- 2. ส่วนดึงข้อมูล Database (สำหรับโชว์ประวัติ Retrain) ---
    versions = ModelVersion.objects.all().order_by('-created_at')
    running_job = RetrainJob.objects.filter(status='Running').first()
    active_db_model = versions.filter(status='Active').first()
    total_recs = Recommendation.objects.count()

    # คำนวณเลขเวอร์ชันถัดไปเผื่อมีการเทรนใหม่
    last_ver = versions.first()
    next_num = 1
    if last_ver:
        try:
            next_num = int(last_ver.version.split('v')[-1]) + 1
        except:
            next_num = versions.count() + 1

    # นำชื่อโมเดลที่รันอยู่ตอนนี้ไปโชว์ให้เว็บรู้
    global CURRENT_MODEL_NAME
    active_filename = CURRENT_MODEL_NAME if 'CURRENT_MODEL_NAME' in globals() else 'Not Loaded'

    context = {
        # ข้อมูลไฟล์สำหรับตาราง Switch Model
        'active_model': active_filename,
        'model_files': model_files,
        
        # ข้อมูล DB เผื่อใช้งานระบบ Retraining
        'versions': versions,
        'running_job': running_job,
        'active_db_model': active_db_model,
        'next_version': next_num,
        'total_recs': total_recs
    }
    return render(request, 'matcher/model_management.html', context)


@require_POST
@user_passes_test(is_admin, login_url='matcher:admin_login')
def switch_model_view(request):
    """
    ฟังก์ชันสลับโมเดล AI เมื่อแอดมินกดปุ่ม Switch
    """
    target_model = request.POST.get('model_name')
    
    # ตรวจสอบว่าไฟล์นั้นมีอยู่จริงในเครื่อง ป้องกัน Error
    model_path = os.path.join(settings.BASE_DIR, target_model)
    
    if target_model and os.path.exists(model_path) and (target_model.endswith('.keras') or target_model.endswith('.h5')):
        # เรียกใช้ฟังก์ชันสลับโมเดลที่เราเขียนไว้ด้านบนของ views.py
        success, message = load_ai_model(target_model)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    else:
        messages.error(request, "Invalid model name or file does not exist in directory.")
        
    return redirect('matcher:model_management')


@require_POST
@user_passes_test(is_admin, login_url='matcher:admin_login')
def upload_model_view(request):
    """
    ฟังก์ชันอัปโหลดไฟล์โมเดล .keras เข้าเครื่องผ่านหน้าเว็บ
    """
    if 'model_file' in request.FILES:
        uploaded_file = request.FILES['model_file']
        file_name = uploaded_file.name
        
        # ตรวจสอบนามสกุลไฟล์
        if not (file_name.endswith('.keras') or file_name.endswith('.h5')):
            messages.error(request, "Invalid file format. Only .keras or .h5 allowed.")
            return redirect('matcher:model_management')

        # บันทึกไฟล์ลงในโฟลเดอร์โปรเจกต์ (BASE_DIR)
        fs = FileSystemStorage(location=settings.BASE_DIR)
        
        # ถ้ามีไฟล์ชื่อเดียวกันอยู่แล้ว ให้เขียนทับ (อัปเดตโมเดล)
        if fs.exists(file_name):
            fs.delete(file_name) 
            
        saved_filename = fs.save(file_name, uploaded_file)
        
        messages.success(request, f"Model '{saved_filename}' uploaded successfully! You can now switch to it.")
    else:
        messages.error(request, "No file selected.")

    return redirect('matcher:model_management')


@require_POST
@user_passes_test(is_admin, login_url='matcher:admin_login')
def start_training(request):
    """
    ฟังก์ชันสำหรับกดปุ่ม Retrain (ถ้าคุณมีฟอร์มเทรนโมเดลใหม่บนหน้าเว็บ)
    """
    # 1. รับค่าจากฟอร์ม
    version_name = request.POST.get('version')
    algorithm = request.POST.get('algorithm')
    data_split = request.POST.get('data_split')
    epoch = request.POST.get('epoch')
    batch_size = request.POST.get('batch_size')
    learning_rate = request.POST.get('learning_rate')
    regularization_type = request.POST.get('regularization_type')
    regularization_rate = request.POST.get('regularization_rate')

    # 2. สร้าง ModelVersion ใหม่ (Status = Training)
    new_model = ModelVersion.objects.create(
        version=version_name,
        algorithm=algorithm,
        status='Training',  # กำลังเทรน
        data_split=data_split,
        epoch=int(epoch) if epoch else 0,
        batch_size=int(batch_size) if batch_size else 0,
        learning_rate=float(learning_rate) if learning_rate else 0.0,
        regularization_type=regularization_type,
        regularization_rate=float(regularization_rate) if regularization_rate else 0.0,
        accuracy=0.0,
        loss=1.0 
    )

    # 3. สร้าง Job ในคิว
    RetrainJob.objects.create(
        model_version=new_model,
        status='Running'
    )

    messages.success(request, f"Started training process for {version_name}!")
    return redirect('matcher:model_management')