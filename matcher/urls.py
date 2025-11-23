from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = "matcher"

urlpatterns = [
    # หน้าแรก
    path("", views.landing_view, name="landing"),
    
    # Login/Register
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path('signup/', views.signup, name='signup'),

    # *** สำคัญ: ต้องมีหน้านี้ ***
    path('scan/', views.scan_face, name='scan'), 

    # หน้าผลลัพธ์
    path("match/", views.match_view, name="match"),
    
    # หน้าอื่นๆ
    path("browse/", views.home, name="home"),
    path("song/<int:song_id>/", views.song_detail, name="song_detail"),
    
    # (ส่วน Backoffice/Admin ปล่อยไว้เหมือนเดิมได้ครับ)
    path("songs/", views.SongListView.as_view(), name="song_list"),
    path("songs/<int:pk>/", views.SongDetailView.as_view(), name="song_detail_crud"),
    path("songs/create/", views.SongCreateView.as_view(), name="song_create"),
    path("songs/<int:pk>/edit/", views.SongUpdateView.as_view(), name="song_update"),
    path("songs/<int:pk>/delete/", views.SongDeleteView.as_view(), name="song_delete"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-users/", views.admin_user_management, name="admin_user_management"),
    path("admin-behavior/", views.admin_behavior, name="admin_behavior"),
    path("admin-songs/", views.admin_song_database, name="admin_song_database"),
    path("admin-categories/", views.admin_category_management, name="admin_category_management"),
    path("admin-model/", views.admin_model, name="admin_model"),
    
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)