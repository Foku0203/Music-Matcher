from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("matcher.urls", namespace="matcher")),  # เพิ่ม namespace
    #path("accounts/", include("accounts.urls")),  # เพิ่มเส้นทางสำหรับแอป accounts
]
    