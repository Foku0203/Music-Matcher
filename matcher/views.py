import os
import cv2
import numpy as np
import tensorflow as tf
from django.conf import settings
from django.contrib import messages 
import random
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage  # <--- เพิ่ม import นี้

# Import Models & Forms
from .models import Song, SongEmotion, User, UserProfile
from .forms import SongForm

# =============================================================================
# 0. AI SETUP (เหมือนเดิม)
# =============================================================================
EMOTION_LABELS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']
MODEL_PATH = os.path.join(settings.BASE_DIR, 'emotion_model_best.keras')
emotion_model = None

try:
    if os.path.exists(MODEL_PATH):
        emotion_model = tf.keras.models.load_model(MODEL_PATH)
        print("✅ AI Model loaded successfully!")
    else:
        print(f"⚠️ Model not found at {MODEL_PATH}")
except Exception as e:
    print(f"❌ Error loading model: {e}")

# =============================================================================
# 1. AUTHENTICATION (เหมือนเดิม - ข้ามส่วนนี้ไป)
# =============================================================================
# ... (ส่วน Login/Signup คงเดิม ไม่ต้องแก้) ...
def landing_view(request):
    return render(request, 'matcher/landing.html')

def user_login(request):
    if request.method == "POST":
        user_input = request.POST.get('username')
        password = request.POST.get('password')
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
# 2. AI SCAN & MATCHING (แก้ไขส่วนนี้)
# =============================================================================

@login_required
def scan_face(request):
    """หน้าอัปโหลดรูป + ประมวลผล AI + แสดงผลลัพธ์ทันที"""
    if request.method == 'POST' and request.FILES.get('face_image'):
        try:
            # 1. รับไฟล์และบันทึกลงเครื่อง (เพื่อให้ HTML ดึงไปแสดงได้)
            myfile = request.FILES['face_image']
            fs = FileSystemStorage()
            
            # บันทึกไฟล์ (Django จะจัดการตั้งชื่อไฟล์ไม่ให้ซ้ำ)
            filename = fs.save(myfile.name, myfile)
            uploaded_file_url = fs.url(filename) # ได้ URL เช่น /media/face.jpg

            # 2. อ่านไฟล์จาก Path ที่บันทึกเพื่อส่งเข้า AI
            file_path = fs.path(filename)
            
            # ใช้ cv2 อ่านจาก path โดยตรง (เสถียรกว่าการอ่านจาก buffer ในบาง environment)
            img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            
            # Preprocess
            img_resized = cv2.resize(img, (48, 48))
            img_array = np.expand_dims(img_resized, axis=0)
            img_array = np.expand_dims(img_array, axis=-1)
            img_array = img_array / 255.0

            # 3. ทำนายผล (Predict)
            if emotion_model:
                prediction = emotion_model.predict(img_array)
                mood_index = np.argmax(prediction)
                predicted_mood = EMOTION_LABELS[mood_index]
                print(f"🤖 AI Predicted: {predicted_mood}")
            else:
                predicted_mood = random.choice(EMOTION_LABELS)

            # 4. ดึงเพลง (Query Songs) - ย้าย Logic มาไว้ที่นี่เลย
            matched_data = (
                SongEmotion.objects
                .filter(emotion__name__iexact=predicted_mood)
                .select_related('song__artist', 'song__album')
                .order_by('?')[:10]
            )
            
            recommended_songs = []
            for item in matched_data:
                recommended_songs.append({
                    "obj": item.song,
                    "genres": [g.genre.name for g in item.song.songgenre_set.all()[:2]]
                })

            # 5. Render หน้า Result ทันที (ส่ง image_url ไปด้วย)
            return render(request, "matcher/match_result.html", {
                "mood_name": predicted_mood,
                "recommended_songs": recommended_songs,
                "image_url": uploaded_file_url  # <--- ตัวแปรสำคัญที่ส่งรูปกลับไปแสดง
            })

        except Exception as e:
            print(f"Error: {e}")
            messages.error(request, f"Error processing image: {e}")

    return render(request, 'matcher/scan.html')

# match_view เดิม (เก็บไว้ก็ได้ เผื่ออยาก test url แบบ manual /match/?mood=Happy)
def match_view(request):
    mood = request.GET.get("mood", "Happy")
    # ... (logic เดิม) ...
    matched_data = SongEmotion.objects.filter(emotion__name__iexact=mood).order_by('?')[:10]
    recommended_songs = [{"obj": item.song} for item in matched_data] # ย่อโค้ดเพื่อความกระชับ
    
    return render(request, "matcher/match_result.html", {
        "mood_name": mood,
        "recommended_songs": recommended_songs,
        "image_url": "https://via.placeholder.com/200" # fallback image ถ้าเข้าผ่าน url นี้
    })

# =============================================================================
# 3. OTHER VIEWS & ADMIN (เหมือนเดิม ไม่ต้องแก้)
# =============================================================================
def home(request):
    qs = Song.objects.filter(is_active=True).order_by("-created_at")
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "matcher/home.html", {"page_obj": page_obj})

def song_detail(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    return render(request, "matcher/song_detail.html", {"song": song})

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