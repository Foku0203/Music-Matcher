from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Song

# หน้า Home (Song List)
def home(request):
    # query เพลง + preload ความสัมพันธ์ (artist, album, genres)
    qs = (
        Song.objects
        .filter(is_active=True)  # แสดงเฉพาะเพลงที่ active
        .select_related("artist", "album")
        .prefetch_related("genres")
        .order_by("title")
    )

    # pagination
    paginator = Paginator(qs, 20)  # 20 เพลงต่อหน้า
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }
    return render(request, "matcher/home.html", context)


# หน้า Song Detail
def song_detail(request, song_id):
    song = get_object_or_404(
        Song.objects.filter(is_active=True)
        .select_related("artist", "album")
        .prefetch_related("genres", "links"),  # preload ลิงก์เพลงด้วย
        pk=song_id
    )

    context = {
        "song": song,
    }
    return render(request, "matcher/song_detail.html", context)
