from django.urls import path
# ถ้ายังไม่มี views ใน accounts ให้ comment บรรทัดนี้ไปก่อน
# from . import views 

# จุดสำคัญ 1: ต้องชื่อ "accounts" ห้ามซ้ำกับ matcher
app_name = "accounts"

urlpatterns = [
    # จุดสำคัญ 2: ห้ามใส่ path("admin/", ...) ในนี้เด็ดขาด!
    
    # ใส่ path ของ accounts เช่น login/logout ตรงนี้
    # path('login/', views.login_view, name='login'),
]