from django.shortcuts import render, redirect

# --- General Views ---
def landing_view(request):
    return render(request, 'matcher/landing.html')

def home_view(request):
    return render(request, 'matcher/home.html')

# --- Auth Views ---
def login_view(request):
    return render(request, 'matcher/login.html')

def signup_view(request):
    return render(request, 'matcher/signup.html')

def logout_view(request):
    # เดี๋ยวค่อยใส่ logic logout จริงๆ
    return redirect('matcher:landing')

# --- Core Features ---
def scan_view(request):
    # หน้านี้ต้องมี Logic เช็ค Login ตาม Flow ที่คุยกัน
    return render(request, 'matcher/scan.html')

def match_result_view(request):
    return render(request, 'matcher/match_result.html')

# --- User Data ---
def dashboard_view(request):
    return render(request, 'matcher/dashboard.html')

def history_view(request):
    return render(request, 'matcher/history.html')

# --- Admin Views ---
def admin_login_view(request):
    return render(request, 'matcher/admin_login.html')

def admin_panel_view(request):
    return render(request, 'matcher/admin_panel.html')