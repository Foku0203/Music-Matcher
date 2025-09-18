from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Song

# หน้า Home
def home(request):
    qs = (Song.objects
          .select_related("artist", "album")
          .prefetch_related("genres")
          .order_by("title"))
    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj}
    return render(request, "matcher/home.html", context)

# รายละเอียดเพลง
def song_detail(request, song_id):
    song = get_object_or_404(
        Song.objects.select_related("artist", "album").prefetch_related("genres"),
        pk=song_id
    )
    context = {"song": song}
    return render(request, "matcher/song_detail.html", context)

# หน้า Login ของ Admin
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        # TODO: ใส่ logic ตรวจสอบรหัสผ่านจริงในอนาคต
        context = {"message": f"ลองล็อกอินด้วย {username}"}
        return render(request, "matcher/admin_dashboard.html", context)

    return render(request, "matcher/admin_login.html")

# หน้า Dashboard ของ Admin

def admin_dashboard(request):
    return render(request, "matcher/admin_dashboard.html")

def admin_user_management(request):
    return render(request, "matcher/admin_user_management.html")

def admin_behavior(request):
    return render(request, "matcher/admin_behavior.html")

def admin_song_database(request):
    return render(request, "matcher/admin_song_database.html")

def admin_category_management(request):
    return render(request, "matcher/admin_category_management.html")

def admin_model(request):
    return render(request, "matcher/admin_model.html")

