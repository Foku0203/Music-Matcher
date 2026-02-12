from django.urls import path
from . import views

app_name = 'matcher'

urlpatterns = [
    # ==============================
    # 🏠 Auth & Public Pages
    # ==============================
    path('', views.landing_view, name='landing'),
    path('home/', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    # ==============================
    # 👤 User Features
    # ==============================
    path('scan/', views.scan_view, name='scan'),
    path('match-result/<int:scan_id>/', views.match_result_view, name='match_result'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('history/', views.history_view, name='history'),
    
    # Profile (ชื่อ function ใน views ไม่มี _view ต่อท้าย)
    path('profile/', views.profile, name='profile'),             
    path('edit-profile/', views.edit_profile, name='edit_profile'),

    # Playlist & Interaction
    path('playlist/add/<int:song_id>/', views.add_to_playlist, name='add_to_playlist'),
    path('api/song-search/', views.song_search_api, name='song_search_api'),
    path('api/feedback/', views.submit_feedback, name='submit_feedback'),

    # ==============================
    # 🛠 Admin Panel
    # ==============================
    path('admin-login/', views.admin_login_view, name='admin_login'),
    
    # จุดที่แก้: เปลี่ยนจาก admin_panel_view เป็น admin_panel เฉยๆ
    path('admin-panel/', views.admin_panel, name='admin_panel'), 
    
    # Function อื่นๆ ใน Admin (ชื่อตาม views.py ล่าสุด)
    path('admin-panel/users/', views.user_management, name='user_management'),
    path('admin-panel/behavior/', views.behavior_analysis, name='behavior_analysis'),
    path('admin-panel/songs/', views.song_database, name='song_database'),
    path('admin-panel/categories/', views.category_management, name='category_management'),
    
    # เพิ่ม Model Management ที่เพิ่งทำไป
    path('admin-panel/models/', views.model_management, name='model_management'),
    path('admin-panel/categories/<int:category_id>/songs/', views.category_songs, name='category_songs'),
]