from django.urls import path
from . import views

# กำหนด namespace ให้เรียกใช้ง่าย (เช่น 'matcher:landing')
app_name = 'matcher'

urlpatterns = [
    # --- General Pages ---
    path('', views.landing_view, name='landing'),          # หน้าแรก (landing.html)
    path('home/', views.home_view, name='home'),           # หน้าหลักสมาชิก (home.html)
    
    # --- Authentication (User) ---
    path('login/', views.login_view, name='login'),        # เข้าสู่ระบบ (login.html)
    path('signup/', views.signup_view, name='signup'),     # สมัครสมาชิก (signup.html)
    path('logout/', views.logout_view, name='logout'),     # ล็อคเอาท์ (Redirect logic)

    # --- Core Features (Music Matcher) ---
    path('scan/', views.scan_view, name='scan'),           # อัปโหลดรูป (scan.html) - FR-02
    path('result/', views.match_result_view, name='result'), # ผลลัพธ์อารมณ์+เพลง (match_result.html) - FR-04,05

    # --- User Data ---
    path('dashboard/', views.dashboard_view, name='dashboard'), # จัดการ Profile (dashboard.html)
    path('history/', views.history_view, name='history'),       # ประวัติการฟัง (history.html)

    # --- Admin Side (Custom) ---
    path('admin-login/', views.admin_login_view, name='admin_login'), # แอดมินล็อกอิน (admin_login.html)
    path('admin-panel/', views.admin_panel_view, name='admin_panel'), # แอดมินแดชบอร์ด (admin_panel.html)
]