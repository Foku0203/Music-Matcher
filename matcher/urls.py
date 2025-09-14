from django.urls import path
from . import views

app_name = 'matcher'

urlpatterns = [
    path('', views.home, name='home'),
    path('song/<int:song_id>/', views.song_detail, name='song_detail'),
]