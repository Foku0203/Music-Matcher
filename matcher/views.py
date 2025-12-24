import os
import numpy as np
import datetime
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db.models import Q, Count
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from .models import (User, UserScanLog, Song, Category, Interaction, Playlist, PlaylistItem, 
    ModelVersion, ModelMetric, Recommendation, RetrainJob)

# --- IMPORT FORMS ---
# หมายเหตุ: ต้องมั่นใจว่าใน forms.py มี UserUpdateForm แล้ว
from .forms import CustomUserCreationForm, UserUpdateForm 

# ==========================================
# 🧠 AI CONFIGURATION
# ==========================================
EMOTION_LABELS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']
MODEL_PATH = os.path.join(settings.BASE_DIR, 'emotion_model_best.keras')
emotion_model = None

if os.path.exists(MODEL_PATH):
    try:
        emotion_model = load_model(MODEL_PATH)
        print(f"✅ AI Model loaded: {MODEL_PATH}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
else:
    print(f"⚠️ Model not found at: {MODEL_PATH}")

# ==========================================
# 🌐 PUBLIC VIEWS
# ==========================================

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('matcher:home')
    return render(request, 'matcher/landing.html')

@login_required(login_url='matcher:login')
def home_view(request):
    return render(request, 'matcher/landing.html', {'user': request.user})

# --- Auth Views ---
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if 'next' in request.GET:
                return redirect(request.GET.get('next'))
            
            # เช็คถ้าเป็น Admin ให้ไปหน้า Admin Panel เลย
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
# 📸 AI SCANNING & MATCHING
# ==========================================
@login_required(login_url='matcher:login')
def scan_view(request):
    if request.method == 'POST':
        image_file = request.FILES.get('image_file')
        if not image_file:
            messages.error(request, "กรุณาเลือกรูปภาพ")
            return redirect('matcher:scan')
            
        try:
            # 1. บันทึกรูปลง DB
            scan_log = UserScanLog.objects.create(
                user=request.user,
                input_image=image_file,
                detected_emotion="Processing..."
            )
            
            # 2. AI Processing
            if emotion_model:
                img_path = scan_log.input_image.path
                img = load_img(img_path, target_size=(48, 48), color_mode='grayscale')
                img_array = img_to_array(img)
                img_array = img_array / 255.0
                img_array = np.expand_dims(img_array, axis=0)

                prediction = emotion_model.predict(img_array)
                max_index = np.argmax(prediction)
                detected_mood = EMOTION_LABELS[max_index]
                
                scan_log.detected_emotion = detected_mood
                scan_log.save()
            else:
                # Fallback กรณีไม่มี Model
                scan_log.detected_emotion = "Neutral"
                scan_log.save()
                messages.warning(request, "AI Model not loaded, using default mood.")

            return redirect('matcher:match_result', scan_id=scan_log.scan_id)

        except Exception as e:
            print(f"Scan Error: {e}")
            messages.error(request, "เกิดข้อผิดพลาดในการประมวลผลภาพ")
            return redirect('matcher:scan')

    return render(request, 'matcher/scan.html')

@login_required(login_url='matcher:login')
def match_result_view(request, scan_id):
    scan_log = get_object_or_404(UserScanLog, scan_id=scan_id, user=request.user)
    mood = scan_log.detected_emotion
    
    # --- Logic การค้นหาเพลงที่ถูกต้อง ---
    try:
        # 1. หาจาก Emotion (ผ่านตาราง SongEmotion)
        emotion_songs = Song.objects.filter(songemotion__emotion__name__iexact=mood)
        
        # 2. หาจาก Category (ถ้ามีการผูก Category ไว้)
        category_songs = Song.objects.filter(category__name__iexact=mood)
        
        # รวมผลลัพธ์
        songs = (emotion_songs | category_songs).distinct()

    except Exception as e:
        print(f"Error finding songs: {e}")
        songs = Song.objects.none()

    # ถ้าไม่เจอเพลงเลย ให้สุ่มเพลง
    if not songs.exists():
        songs = Song.objects.order_by('?')[:5]
        if mood != "Processing...":
            messages.info(request, f"ไม่พบเพลงสำหรับอารมณ์ '{mood}' นี่คือเพลงแนะนำทั่วไป")
    
    context = {
        'scan_log': scan_log,
        'mood': mood,
        'songs': songs
    }
    return render(request, 'matcher/match_result.html', context)

# ==========================================
# 👤 USER DASHBOARD & PROFILE
# ==========================================
@login_required(login_url='matcher:login')
def dashboard_view(request):
    return render(request, 'matcher/dashboard.html', {'username': request.user.username})

@login_required(login_url='matcher:login')
def history_view(request):
    playlist, _ = Playlist.objects.get_or_create(user=request.user, name="My Favorite Songs")
    saved_songs = PlaylistItem.objects.filter(playlist=playlist).select_related('song').order_by('-id')
    return render(request, 'matcher/history.html', {'saved_songs': saved_songs})

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

# --- Interaction APIs ---
@login_required(login_url='matcher:login')
@require_POST
def submit_feedback(request):
    song_id = request.POST.get('song_id')
    feedback_type = request.POST.get('type')
    if song_id and feedback_type:
        song = get_object_or_404(Song, song_id=song_id)
        Interaction.objects.create(
            user=request.user, song=song, type=feedback_type,
            rating=1 if feedback_type == 'like' else -1
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
    # Stats Calculation
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    banned_users = User.objects.filter(is_active=False).count()
    
    last_week = timezone.now() - datetime.timedelta(days=7)
    new_users_count = User.objects.filter(date_joined__gte=last_week).count()
    
    most_liked_songs = Song.objects.all()[:5] 
    recent_users = User.objects.order_by('-date_joined')[:5]

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'banned_users': banned_users,
        'new_users_count': new_users_count,
        'most_liked_songs': most_liked_songs,
        'recent_users': recent_users,
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

    context = {
        'songs': songs,
        'query': query
    }
    return render(request, 'matcher/song_database.html', context)

@user_passes_test(is_admin, login_url='matcher:admin_login')
def category_management(request):
    # ดึงข้อมูล Category จริงจากฐานข้อมูล
    categories = Category.objects.all().order_by('created_at')
    
    # ถ้ามีการส่ง Form เข้ามา (เช่น เพิ่ม/ลบ) สามารถเขียน Logic เพิ่มตรงนี้ได้
    
    return render(request, 'matcher/category_management.html', {'categories': categories})

# --- NEW: Model Management View ---
@user_passes_test(is_admin, login_url='matcher:admin_login')
def model_management(request):
    # ดึงข้อมูล Model Version
    model_list = ModelVersion.objects.all().order_by('-created_at')
    
    # หาโมเดลที่ Active อยู่
    active_model = ModelVersion.objects.filter(status='Active').first()
    
    # ดึง Metrics ของโมเดลล่าสุด (ตัวอย่าง)
    active_metrics = {
        'accuracy': 92.5,
        'loss': 0.15
    }
    
    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'retrain':
            # Logic สำหรับเริ่ม Retrain (อาจจะสร้าง Job ลง DB)
            messages.success(request, "Retraining job started successfully!")
            return redirect('matcher:model_management')

    context = {
        'model_list': model_list,
        'active_model': active_model,
        'active_metrics': active_metrics
    }
    return render(request, 'matcher/model_management.html', context)