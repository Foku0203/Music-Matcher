from django.core.management.base import BaseCommand
from django.utils import timezone
from matcher.models import Artist, Album, Song, Genre, Emotion, SongEmotion, SongLink
import random

class Command(BaseCommand):
    help = "Seed Thai songs dataset (210 songs, 7 emotions × 30 songs)"

    def handle(self, *args, **options):
        # 7 emotions
        emotions = ["Happy", "Sad", "Angry", "Surprise", "Fear", "Disgust", "Neutral"]
        emotion_objs = {}
        for e in emotions:
            obj, _ = Emotion.objects.get_or_create(name=e)
            emotion_objs[e] = obj
        self.stdout.write(self.style.SUCCESS("Emotions created."))

        # Genres
        genres = ["Pop", "Rock", "Indie", "R&B", "HipHop", "Ballad", "Dance"]
        genre_objs = {}
        for g in genres:
            obj, _ = Genre.objects.get_or_create(name=g)
            genre_objs[g] = obj
        self.stdout.write(self.style.SUCCESS("Genres created."))

        # Create artists, albums, songs
        song_count = 0
        for e in emotions:
            for i in range(1, 31):  # 30 songs per emotion
                artist_name = f"ศิลปิน{e}{i}"
                album_title = f"อัลบั้ม{e}{i}"
                song_title = f"เพลง{e}{i}"

                artist, _ = Artist.objects.get_or_create(name=artist_name)
                album, _ = Album.objects.get_or_create(artist=artist, title=album_title, year=2025)
                song, created = Song.objects.get_or_create(
                    title=song_title,
                    artist=artist,
                    album=album,
                    defaults={
                        "duration": random.randint(180, 300),  # 3–5 นาที
                        "language": "th",
                        "release_date": timezone.now().date(),
                        "is_active": True,
                    }
                )
                if created:
                    # random genre
                    song.genres.add(random.choice(list(genre_objs.values())))

                    # Emotion mapping
                    SongEmotion.objects.get_or_create(
                        song=song,
                        emotion=emotion_objs[e],
                        defaults={"confidence": 1.0, "source": "manual"},
                    )

                    # Song links (mock)
                    SongLink.objects.get_or_create(
                        song=song,
                        platform="youtube",
                        defaults={"url": f"https://youtube.com/watch?v={e}{i}demo"}
                    )
                    SongLink.objects.get_or_create(
                        song=song,
                        platform="spotify",
                        defaults={"url": f"https://open.spotify.com/track/{e}{i}demo"}
                    )

                    song_count += 1

        self.stdout.write(self.style.SUCCESS(f"Seed completed: {song_count} songs created."))
