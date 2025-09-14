from django.core.management.base import BaseCommand
from matcher.models import Artist, Album, Genre, Song, SongGenre, Emotion, SongEmotion

class Command(BaseCommand):
    help = "Seed minimal music data for demo (artists, albums, songs, genres, emotions)"

    def handle(self, *args, **options):
        # Artists
        a1, _ = Artist.objects.get_or_create(name="Artist A")
        a2, _ = Artist.objects.get_or_create(name="Artist B")

        # Albums (ใช้ฟิลด์ year ของคุณ)
        alb1, _ = Album.objects.get_or_create(artist=a1, title="Album A1", defaults={"year": 2020})
        alb2, _ = Album.objects.get_or_create(artist=a2, title="Album B1", defaults={"year": 2021})

        # Genres
        pop, _ = Genre.objects.get_or_create(name="Pop")
        rock, _ = Genre.objects.get_or_create(name="Rock")

        # Songs (album เป็น SET_NULL ได้ แต่ใน seed นี้ผูกให้เห็นภาพ)
        s1, _ = Song.objects.get_or_create(title="Shine", artist=a1, album=alb1)
        s2, _ = Song.objects.get_or_create(title="Storm", artist=a2, album=alb2)

        # SongGenre
        SongGenre.objects.get_or_create(song=s1, genre=pop)
        SongGenre.objects.get_or_create(song=s2, genre=rock)

        # Emotions
        happy, _ = Emotion.objects.get_or_create(name="happy")
        sad, _   = Emotion.objects.get_or_create(name="sad")

        # SongEmotion
        SongEmotion.objects.update_or_create(song=s1, emotion=happy, defaults={"confidence": 0.812, "source": "manual"})
        SongEmotion.objects.update_or_create(song=s2, emotion=sad, defaults={"confidence": 0.640, "source": "ml"})

        self.stdout.write(self.style.SUCCESS("Seeded demo data (artists/albums/songs/genres/emotions)"))
