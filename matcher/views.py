import os
import cv2
import numpy as np
import tensorflow as tf
import random

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage

# Import Models & Forms
from .models import Song, SongEmotion, User, UserProfile
from .forms import SongForm

# =============================================================================
# 0. AI SETUP & CONFIGURATION
# =============================================================================
# ลาเบลผลลัพธ์จาก AI (7 อารมณ์มาตรฐาน)
EMOTION_LABELS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# พยายามโหลด Model (เช็คชื่อไฟล์ให้ตรงกับที่คุณมีในโปรเจกต์)
# แนะนำให้วางไฟล์โมเดลไว้ที่ Base Directory (ที่เดียวกับ manage.py)
MODEL_PATH = os.path.join(settings.BASE_DIR, 'emotion_model_best.keras') 
# หรือถ้าใช้ชื่ออื่น เช่น 'model_fer2013.h5' ให้แก้ตรงนี้

emotion_model = None

try:
    if os.path.exists(MODEL_PATH):
        emotion_model = tf.keras.models.load_model(MODEL_PATH)
        print(f"✅ AI Model loaded successfully from: {MODEL_PATH}")
    else:
        print(f"⚠️ Warning: Model not found at {MODEL_PATH}. AI will run in Mock mode.")
except Exception as e:
    print(f"❌ Error loading model: {e}")

# =============================================================================
# 1. AUTHENTICATION (Login / Logout / Signup)
# =============================================================================

def landing_view(request):
    return render(request, 'matcher/landing.html')

def user_login(request):
    if request.method == "POST":
        user_input = request.POST.get('username')
        password = request.POST.get('password')
        
        # รองรับการ Login ด้วย Email
        if '@' in user_input:
            try:
                user_obj = User.objects.get(email=user_input)
                user_input = user_obj.username
            except User.DoesNotExist:
                pass
        
        user = authenticate(request, username=user_input, password=password)
        if user is not None:
            login(request, user)
            return redirect('matcher:landing')
        else:
            messages.error(request, "Invalid username/email or password.")
    
    form = AuthenticationForm()
    return render(request, 'matcher/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('matcher:landing')

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')
        
        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect('matcher:signup')
        
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            UserProfile.objects.create(
                user=user, 
                age=request.POST.get('age'), 
                gender=request.POST.get('gender'), 
                province=request.POST.get('province')
            )
            messages.success(request, "Account created! Please login.")
            return redirect('matcher:login')
        except Exception as e:
            messages.error(request, str(e))
            return redirect('matcher:signup')
            
    return render(request, 'matcher/signup.html')

# =============================================================================
# 2. AI SCAN & MATCHING (ส่วนสำคัญที่สุด)
# =============================================================================

@login_required
def scan_face(request):
    """
    รับรูปภาพ -> AI วิเคราะห์ 7 อารมณ์ -> แปลงเป็น 4 อารมณ์ -> ค้นหาเพลง
    """
    if request.method == 'POST' and request.FILES.get('face_image'):
        try:
            # --- Step 1: Save Image ---
            myfile = request.FILES['face_image']
            fs = FileSystemStorage()
            filename = fs.save(myfile.name, myfile)
            uploaded_file_url = fs.url(filename)
            file_path = fs.path(filename)

            # --- Step 2: Preprocess Image ---
            # อ่านไฟล์ด้วย OpenCV
            img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            
            # ถ้าอ่านไฟล์ไม่ได้ (ไฟล์เสีย)
            if img is None:
                messages.error(request, "Invalid image file.")
                return render(request, 'matcher/scan.html')

            # Resize ให้เข้ากับ Model (48x48)
            img_resized = cv2.resize(img, (48, 48))
            img_array = np.expand_dims(img_resized, axis=0)
            img_array = np.expand_dims(img_array, axis=-1)
            img_array = img_array / 255.0

            # --- Step 3: AI Prediction (7 Emotions) ---
            raw_mood = "Neutral" # ค่าเริ่มต้น
            
            if emotion_model:
                prediction = emotion_model.predict(img_array)
                mood_index = np.argmax(prediction)
                raw_mood = EMOTION_LABELS[mood_index]
                print(f"🤖 AI Raw Result: {raw_mood}")
            else:
                # กรณีโหลด Model ไม่ได้ จะสุ่มเอา (สำหรับ Dev)
                raw_mood = random.choice(EMOTION_LABELS)

            # --- Step 4: 🔥 MAPPING 7 -> 4 MOODS 🔥 ---
            # นี่คือหัวใจสำคัญที่ทำให้หาเพลงเจอ
            mood_mapper = {
                # Happy Group
                'Happy': 'Happy',
                'Surprise': 'Happy',

                # Sad Group
                'Sad': 'Sad',

                # Angry Group (รวม Fear, Disgust)
                'Angry': 'Angry',
                'Disgust': 'Angry',
                'Fear': 'Angry',

                # Neutral Group
                'Neutral': 'Neutral'
            }

            # แปลงค่า (ถ้าไม่เจอใน map ให้เป็น Neutral)
            final_mood = mood_mapper.get(raw_mood, 'Neutral')
            print(f"✅ Mapped to Database Category: {final_mood}")

            # --- Step 5: Query Database ---
            matched_data = (
                SongEmotion.objects
                .filter(emotion__name__iexact=final_mood)  # ใช้ค่าที่แปลงแล้วค้นหา
                .select_related('song', 'song__artist', 'song__album')
                .order_by('?')[:50]
            )

            # แปลงข้อมูลให้ Template ใช้ง่ายๆ
            recommended_songs = []
            for item in matched_data:
                recommended_songs.append({
                    "obj": item.song,
                    "genres": [g.genre.name for g in item.song.songgenre_set.all()[:2]]
                })

            # --- Step 6: Return Result ---
            context = {
                "mood_name": final_mood,      # อารมณ์ที่ใช้หาเพลง (4 แบบ)
                "raw_mood": raw_mood,         # อารมณ์ดิบจาก AI (7 แบบ) - เผื่ออยากโชว์
                "recommended_songs": recommended_songs,
                "image_url": uploaded_file_url
            }
            return render(request, "matcher/match_result.html", context)

        except Exception as e:
            print(f"❌ Error in scan_face: {e}")
            messages.error(request, f"Error processing request: {e}")
            return render(request, 'matcher/scan.html')

    # กรณีไม่ใช่ POST หรือไม่มีรูป
    return render(request, 'matcher/scan.html')


def match_view(request):
    """(Optional) สำหรับ Test ผ่าน URL parameter เช่น /match/?mood=Happy"""
    mood = request.GET.get("mood", "Happy")
    
    # Mapping Logic (ใส่ไว้เหมือนกันเผื่อ Manual Test)
    mood_mapper = {
        'Happy': 'Happy', 'Surprise': 'Happy',
        'Sad': 'Sad',
        'Angry': 'Angry', 'Disgust': 'Angry', 'Fear': 'Angry',
        'Neutral': 'Neutral'
    }
    final_mood = mood_mapper.get(mood, 'Neutral')

    matched_data = SongEmotion.objects.filter(emotion__name__iexact=final_mood).order_by('?')[:10]
    recommended_songs = [{"obj": item.song} for item in matched_data]
    
    return render(request, "matcher/match_result.html", {
        "mood_name": final_mood,
        "recommended_songs": recommended_songs,
        "image_url": "https://via.placeholder.com/300?text=Manual+Test"
    })

# =============================================================================
# 3. GENERAL VIEWS & CRUD
# =============================================================================

def home(request):
    qs = Song.objects.filter(is_active=True).order_by("-created_at")
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "matcher/home.html", {"page_obj": page_obj})

def song_detail(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    return render(request, "matcher/song_detail.html", {"song": song})

# Class-Based Views
class SongListView(ListView):
    model = Song
    template_name = "matcher/song_list.html"
    context_object_name = "songs"

class SongDetailView(DetailView):
    model = Song
    template_name = "matcher/song_detail.html"

class SongCreateView(CreateView):
    model = Song
    form_class = SongForm
    template_name = "matcher/song_form.html"
    success_url = reverse_lazy("matcher:song_list")

class SongUpdateView(UpdateView):
    model = Song
    form_class = SongForm
    template_name = "matcher/song_form.html"
    success_url = reverse_lazy("matcher:song_list")

class SongDeleteView(DeleteView):
    model = Song
    template_name = "matcher/song_confirm_delete.html"
    success_url = reverse_lazy("matcher:song_list")

# =============================================================================
# 4. ADMIN CUSTOM VIEWS
# =============================================================================

def admin_login(request):
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user and user.is_staff:
            login(request, user)
            return redirect('matcher:admin_dashboard')
    return render(request, 'matcher/admin_login.html')

def admin_dashboard(request): return render(request, "matcher/admin_dashboard.html")
def admin_user_management(request): return render(request, "matcher/admin_user_management.html")
def admin_behavior(request): return render(request, "matcher/admin_behavior.html")
def admin_song_database(request): return render(request, "matcher/admin_song_database.html")
def admin_category_management(request): return render(request, "matcher/admin_category_management.html")
def admin_model(request): return render(request, "matcher/admin_model.html")