from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Song
from .forms import SongForm   # ✅ ใช้ฟอร์มที่เราสร้างเอง

# ===================== HOME =====================

def home(request):
    qs = (
        Song.objects
        .select_related("artist", "album")
        .prefetch_related("genres")
        .order_by("-id")  # เพลงล่าสุดอยู่บนสุด
    )
    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj}
    return render(request, "matcher/home.html", context)


# ===================== CRUD SONG =====================

class SongListView(ListView):
    model = Song
    template_name = "matcher/song_list.html"
    context_object_name = "songs"
    paginate_by = 10   # ✅ แสดง 10 เพลงต่อหน้า
    ordering = ["-id"] # ✅ เพลงใหม่ล่าสุดอยู่บนสุด


class SongDetailView(DetailView):
    model = Song
    template_name = "matcher/song_detail.html"


class SongCreateView(CreateView):
    model = Song
    form_class = SongForm   # ✅ ใช้ฟอร์มที่กำหนดเอง
    template_name = "matcher/song_form.html"
    success_url = reverse_lazy("matcher:song_list")


class SongUpdateView(UpdateView):
    model = Song
    form_class = SongForm   # ✅ ใช้ฟอร์มที่กำหนดเอง
    template_name = "matcher/song_form.html"
    success_url = reverse_lazy("matcher:song_list")


class SongDeleteView(DeleteView):
    model = Song
    template_name = "matcher/song_confirm_delete.html"
    success_url = reverse_lazy("matcher:song_list")


# ===================== OLD SONG DETAIL (ใช้ใน home) =====================

def song_detail(request, song_id):
    song = get_object_or_404(
        Song.objects.select_related("artist", "album").prefetch_related("genres"),
        pk=song_id
    )
    context = {"song": song}
    return render(request, "matcher/song_detail.html", context)


# ===================== ADMIN PAGES =====================

def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        # TODO: ใส่ logic ตรวจสอบรหัสผ่านจริงในอนาคต
        context = {"message": f"ลองล็อกอินด้วย {username}"}
        return render(request, "matcher/admin_dashboard.html", context)

    return render(request, "matcher/admin_login.html")


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
