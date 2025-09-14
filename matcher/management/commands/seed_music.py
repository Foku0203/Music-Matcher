# matcher/management/commands/seed_music.py
from django.core.management.base import BaseCommand
from matcher.models import Artist, Album, Genre, Song

class Command(BaseCommand):
    help = "Seed minimal music data using current models only"

    def handle(self, *args, **options):
        # Artists
        a1, _ = Artist.objects.get_or_create(name="Artist A")
        a2, _ = Artist.objects.get_or_create(name="Artist B")

        # Genres
        pop, _ = Genre.objects.get_or_create(name="Pop")
        rock, _ = Genre.objects.get_or_create(name="Rock")

        # Albums (ใส่ year ให้ครบ เพราะฟิลด์ you เป็น required ใน models ตอนนี้)
        alb1, _ = Album.objects.get_or_create(artist=a1, title="Album A1", year=2020)
        alb2, _ = Album.objects.get_or_create(artist=a2, title="Album B1", year=2021)

        # Songs
        s1, _ = Song.objects.get_or_create(title="Song A1", artist=a1, album=alb1)
        s2, _ = Song.objects.get_or_create(title="Song B1", artist=a2, album=alb2)

        # Genres M2M (add ตรง ๆ ได้ ไม่ต้องผ่าน SongGenre โดยตรง)
        s1.genres.add(pop)
        s2.genres.add(rock, pop)

        self.stdout.write(self.style.SUCCESS("Seeded sample data successfully."))
