from django.shortcuts import render, get_object_or_404
from .models import Song
from django.core.paginator import Paginator

def home(request):
    qs = (Song.objects
          .select_related("artist","album")
          .prefetch_related("genres")
          .order_by("title"))
    paginator = Paginator(qs, 20)  # สร้าง Paginator object
    page_number = request.GET.get("page")  # ดึงหมายเลขหน้าจาก request
    page_obj = paginator.get_page(page_number)  # ดึง object ของหน้านั้น

    context = {
        "page_obj": page_obj,
    }
    return render(request, "matcher/home.html", context)

def song_detail(request, song_id):
    song = get_object_or_404(
        Song.objects.select_related("artist", "album").prefetch_related("genres"),
        pk=song_id
    )
    context = {
        "song": song,
    }
    return render(request, "matcher/song_detail.html", context)