from django.urls import path
from . import views

app_name = 'matcher'

urlpatterns = [
    # ==============================
    # 🏠 General & Auth
    # ==============================
    path('', views.landing_view, name='landing'),
    path('home/', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    # ==============================
    # 👤 User Profile & Dashboard
    # ==============================
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('history/', views.history_view, name='history'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # ==============================
    # 📸 Scan & Result
    # ==============================
    path('scan/', views.scan_view, name='scan'),
    path('match-result/<int:scan_id>/', views.match_result_view, name='match_result'),
    path('browse/', views.browse_view, name='browse'),

    # ==============================
    # 🎵 Playlist & Interaction
    # ==============================
    path('playlist/add/<int:song_id>/', views.add_to_playlist, name='add_to_playlist'),
    path('api/feedback/', views.submit_feedback, name='submit_feedback'),
    path('api/search/', views.song_search_api, name='song_search_api'),
    path('favorite/toggle/<int:song_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('interaction/<int:song_id>/<str:action_type>/', views.record_interaction, name='record_interaction'),

    # ==============================
    # 🛠 Admin Panel (Custom)
    # ==============================
    path('admin-custom/login/', views.admin_login_view, name='admin_login'),
    path('admin-custom/', views.admin_panel, name='admin_panel'),
    path('admin-custom/users/', views.user_management, name='user_management'),
    path('admin-custom/behavior/', views.behavior_analysis, name='behavior_analysis'),
    path('admin-custom/users/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('admin-custom/users/delete/<int:user_id>/', views.delete_user, name='delete_user'),

    # --- Song Management ---
    path('admin-custom/songs/', views.song_database, name='song_database'),
    path('admin-custom/songs/save/', views.save_song, name='save_song'),
    # เพิ่ม Path นี้เพื่อให้ปุ่มลบเพลงทำงานได้
    path('admin-custom/songs/delete/<int:song_id>/', views.delete_song, name='delete_song'),

    # --- Category Management (จัดระเบียบใหม่) ---
    path('admin-custom/categories/', views.category_management, name='category_management'),
    path('admin-custom/categories/save/', views.save_category, name='save_category'),
    path('admin-custom/categories/delete/<int:cat_id>/', views.delete_category, name='delete_category'),
    path('admin-custom/categories/view/<int:cat_id>/', views.category_songs, name='category_songs'),

    # --- AI Model ---
    path('admin-custom/models/', views.model_management, name='model_management'),
    path('admin-custom/models/train/', views.start_training, name='start_training'),
    path('panel/switch-model/', views.switch_model_view, name='switch_model'),
    path('panel/upload-model/', views.upload_model_view, name='upload_model'),

    # ==============================
    # 📥 System / Import Data
    # ==============================
    path('system/import-songs/', views.import_songs_from_json, name='import_songs'),
]