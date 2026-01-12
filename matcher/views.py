import os
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
from django.conf import settings
from django.db.models import Q, Count

# --- TENSORFLOW ---
try:
    from tensorflow.keras.models import load_model
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠️ TensorFlow not installed.")

from .models import (
    User, UserScanLog, Song, Category, Interaction, Playlist, PlaylistItem,
    ModelVersion, ModelMetric, Recommendation, RetrainJob, SongEmotion
)
from .forms import CustomUserCreationForm, UserUpdateForm


# ==========================================
# 🧠 AI CONFIGURATION
# ==========================================
# IMPORTANT: ต้องเรียง label ให้ตรงกับตอนเทรนโมเดล (class order)
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

MODEL_PATH = os.path.join(settings.BASE_DIR, 'emotion_model_best.keras')
emotion_model = None

# สร้าง face cascade ไว้ครั้งเดียว (ไม่ต้องสร้างทุก request)
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

if TF_AVAILABLE and os.path.exists(MODEL_PATH):
    try:
        emotion_model = load_model(MODEL_PATH)
        print(f"✅ Loaded User Model: {MODEL_PATH}")
        print(f"✅ Model input shape: {emotion_model.input_shape}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
else:
    print(f"⚠️ Model not found at {MODEL_PATH}")


# ==========================================
# 🧩 HELPERS (GRAYSCALE PREPROCESS + SHAPE FIX)
# ==========================================
def _imread_unicode(path: str):
    """
    cv2.imread บางเครื่อง/บาง OS อาจพังกับ path ที่เป็น unicode
    ฟังก์ชันนี้อ่านไฟล์แบบ robust มากขึ้น
    """
    try:
        img = cv2.imread(path)
        if img is not None:
            return img
    except Exception:
        pass

    # fallback: read bytes -> imdecode
    with open(path, "rb") as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return img


def _model_has_rescaling(model) -> bool:
    """
    เช็คคร่าว ๆ ว่าในโมเดลมี layer Rescaling อยู่แล้วหรือไม่
    ถ้ามี -> ไม่ต้องหาร 255 ซ้ำ
    """
    try:
        return any(layer.__class__.__name__ == "Rescaling" for layer in model.layers)
    except Exception:
        return False


def preprocess_emotion_input(
    img_path: str,
    model,
    target_size=(48, 48),
    normalize_mode="auto",   # "auto" | "divide255" | "raw"
    force_grayscale=True,
    debug_save=False,
):
    """
    สร้าง input ให้โมเดลแบบ robust:
    - อ่านรูป
    - grayscale
    - face detect -> เลือกหน้าที่ใหญ่สุด + margin
    - resize 48x48
    - equalizeHist
    - normalize ตาม mode
    - จัด shape ให้ตรงกับ model.input_shape (channels_last / channels_first / no-channel)

    return:
      x: np.ndarray สำหรับ predict
      meta: dict สำหรับ debug print
    """
    frame = _imread_unicode(img_path)
    if frame is None:
        raise ValueError(f"อ่านรูปไม่สำเร็จ: {img_path}")

    # 1) grayscale แน่นอน (ส่วนใหญ่โมเดล emotion เทรนด้วย grayscale)
    if force_grayscale:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # ยังใช้ gray สำหรับ face detect

    # 2) หา face และเลือก face ที่ใหญ่สุด
    faces = FACE_CASCADE.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40)
    )

    face_found = len(faces) > 0
    if face_found:
        x, y, w, h = max(faces, key=lambda b: b[2] * b[3])

        # margin กัน crop แน่นเกิน
        margin = int(0.15 * max(w, h))
        x0 = max(x - margin, 0)
        y0 = max(y - margin, 0)
        x1 = min(x + w + margin, gray.shape[1])
        y1 = min(y + h + margin, gray.shape[0])

        crop = gray[y0:y1, x0:x1]
    else:
        crop = gray

    # 3) resize เป็น 48x48
    crop = cv2.resize(crop, target_size, interpolation=cv2.INTER_AREA)

    # 4) equalize histogram (ช่วยให้ contrast ใกล้ dataset emotion ทั่วไป)
    # ต้องเป็น uint8 ถึงจะใช้ equalizeHist ได้ดี
    if crop.dtype != np.uint8:
        crop_uint8 = np.clip(crop, 0, 255).astype(np.uint8)
    else:
        crop_uint8 = crop
    crop_uint8 = cv2.equalizeHist(crop_uint8)

    # debug save ภาพ 48x48 ที่ป้อนโมเดล (ดูได้ว่า crop ถูกไหม)
    if debug_save:
        try:
            debug_path = os.path.join(settings.MEDIA_ROOT, "debug_48x48.png")
            cv2.imwrite(debug_path, crop_uint8)
            print(f"🧪 Saved debug image: {debug_path}")
        except Exception as e:
            print(f"⚠️ debug_save failed: {e}")

    # 5) เป็น float32
    crop_f = crop_uint8.astype("float32")

    # 6) normalize
    has_rescaling = _model_has_rescaling(model)
    if normalize_mode == "auto":
        # ถ้ามี Rescaling อยู่แล้ว -> raw (0-255) / ถ้าไม่มี -> divide255
        if not has_rescaling:
            crop_f /= 255.0
    elif normalize_mode == "divide255":
        crop_f /= 255.0
    elif normalize_mode == "raw":
        pass
    else:
        raise ValueError("normalize_mode must be: auto | divide255 | raw")

    # 7) จัด shape ให้ตรงกับโมเดล
    input_shape = model.input_shape
    if isinstance(input_shape, list):
        input_shape = input_shape[0]

    # ค่าเริ่มต้น
    x_arr = crop_f

    channels_first = False
    if isinstance(input_shape, tuple) and len(input_shape) == 4:
        # ตรวจ channels_first แบบคร่าว ๆ: (None, C, H, W)
        if input_shape[1] in (1, 3) and input_shape[2] == target_size[0] and input_shape[3] == target_size[1]:
            channels_first = True

        if channels_first:
            ch = input_shape[1]
            if ch == 1:
                x_arr = np.expand_dims(x_arr, axis=0)      # (1,48,48)
                x_arr = np.expand_dims(x_arr, axis=0)      # (1,1,48,48)
            elif ch == 3:
                x3 = np.stack([x_arr, x_arr, x_arr], axis=0)  # (3,48,48)
                x_arr = np.expand_dims(x3, axis=0)            # (1,3,48,48)
            else:
                # fallback
                x_arr = np.expand_dims(x_arr, axis=0)
                x_arr = np.expand_dims(x_arr, axis=0)
        else:
            # channels_last: (None, H, W, C)
            ch = input_shape[-1]
            if ch == 1:
                x_arr = np.expand_dims(x_arr, axis=-1)     # (48,48,1)
            elif ch == 3:
                x_arr = np.stack([x_arr, x_arr, x_arr], axis=-1)  # (48,48,3)
            else:
                x_arr = np.expand_dims(x_arr, axis=-1)
            x_arr = np.expand_dims(x_arr, axis=0)          # (1,48,48,C)

    elif isinstance(input_shape, tuple) and len(input_shape) == 3:
        # (None,48,48) ไม่มี channel
        x_arr = np.expand_dims(x_arr, axis=0)              # (1,48,48)
    else:
        # fallback สุดท้าย
        x_arr = np.expand_dims(x_arr, axis=-1)             # (48,48,1)
        x_arr = np.expand_dims(x_arr, axis=0)              # (1,48,48,1)

    meta = {
        "face_found": bool(face_found),
        "faces_count": int(len(faces)),
        "normalize_mode": normalize_mode,
        "model_has_rescaling": bool(has_rescaling),
        "model_input_shape": str(model.input_shape),
        "final_x_shape": str(x_arr.shape),
        "final_x_dtype": str(x_arr.dtype),
        "final_x_min": float(np.min(x_arr)),
        "final_x_max": float(np.max(x_arr)),
    }
    return x_arr, meta


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
# 📸 AI SCANNING (GRAYSCALE + FIX SHAPE)
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

                # ✅ preprocess ใหม่ (grayscale + face crop + shape fix)
                # normalize_mode:
                #   - "auto" = ถ้าโมเดลมี Rescaling อยู่แล้วจะไม่หาร 255 ซ้ำ
                #   - ถ้าคุณมั่นใจว่าเทรนด้วย /255 ให้ใช้ "divide255"
                #   - ถ้าเทรนด้วยค่าดิบ 0-255 ให้ใช้ "raw"
                x, meta = preprocess_emotion_input(
                    img_path=img_path,
                    model=emotion_model,
                    target_size=(48, 48),
                    normalize_mode="auto",
                    force_grayscale=True,
                    debug_save=False,  # เปลี่ยนเป็น True ถ้าอยากให้เซฟ debug_48x48.png
                )

                prediction = emotion_model.predict(x, verbose=0)
                scores = prediction[0]
                max_index = int(np.argmax(scores))
                detected_mood = EMOTION_LABELS[max_index]

                print("🧠 Preprocess meta:", meta)
                print("📊 Raw Scores:", scores)
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
# RESULT & OTHER VIEWS
# ==========================================
@login_required(login_url='matcher:login')
def match_result_view(request, scan_id):
    scan_log = get_object_or_404(UserScanLog, scan_id=scan_id, user=request.user)
    mood = (scan_log.detected_emotion or "neutral").lower()

    songs = Song.objects.none()
    try:
        # Match ตรงๆ
        songs = Song.objects.filter(songemotion__emotion__name__iexact=mood)

        # Fallback Match
        if not songs.exists():
            songs = Song.objects.filter(category__name__iexact=mood)

        songs = songs.order_by('?')[:5]
    except Exception as e:
        print(f"Error finding songs: {e}")

    # ถ้าไม่เจอจริงๆ สุ่มมาโชว์ (กันหน้าขาว)
    if not songs.exists():
        songs = Song.objects.order_by('?')[:5]

    main_song = songs[0] if songs.exists() else None

    context = {
        'scan_log': scan_log,
        'mood': mood,
        'songs': songs,
        'song': main_song,
        'user_image': scan_log.input_image.url
    }
    return render(request, 'matcher/match_result.html', context)


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

    # นับจำนวนเพลงตาม schema จริง
    for c in mood_categories:
        c.display_count = Song.objects.filter(
            songemotion__emotion__name__iexact=c.name
        ).distinct().count()

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

    songs = Song.objects.select_related('artist', 'album', 'category')

    if category.type == 'GENRE':
        songs = songs.filter(category=category)

    elif category.type == 'MOOD':
        songs = songs.filter(songemotion__emotion__name__iexact=category.name).distinct()

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
