from django.core.management.base import BaseCommand
from django.utils import timezone
from matcher.models import Artist, Album, Song, Genre, Emotion, SongEmotion, SongLink
import random

class Command(BaseCommand):
    help = "Seed Thai songs dataset (210 songs, 7 emotions × 30 songs each)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🎵 Starting seed process..."))

        # -------------------------------
        # 1. สร้าง Emotion
        # -------------------------------
        emotions = ["Happy", "Sad", "Angry", "Surprise", "Fear", "Disgust", "Neutral"]
        emotion_objs = {e: Emotion.objects.get_or_create(name=e)[0] for e in emotions}
        self.stdout.write(self.style.SUCCESS(f"✔ Created {len(emotion_objs)} emotions."))

        # -------------------------------
        # 2. สร้าง Genre
        # -------------------------------
        genres = ["Pop", "Rock", "Indie", "R&B", "HipHop", "Ballad", "Dance"]
        genre_objs = {g: Genre.objects.get_or_create(name=g)[0] for g in genres}
        self.stdout.write(self.style.SUCCESS(f"✔ Created {len(genre_objs)} genres."))

        # -------------------------------
        # 3. Loop สร้าง Artist, Album, Song
        # -------------------------------
        song_count = 0
        for e in emotions:
            for i in range(1, 31):  # 30 songs per loop
                artist_name = f"ศิลปิน {e} {i}"
                album_title = f"อัลบั้ม {e} {i}"
                song_title = f"เพลง {e} {i}"

                # Artist
                artist, _ = Artist.objects.get_or_create(
                    name=artist_name,
                    defaults={"slug": f"{e.lower()}-{i}-{random.randint(1000,9999)}"},  # กัน slug ซ้ำ
                )

                # Album
                album, _ = Album.objects.get_or_create(
                    artist=artist,
                    title=album_title,
                    defaults={"year": 2025},
                )

                # Song
                song, created = Song.objects.get_or_create(
                    title=song_title,
                    artist=artist,
                    album=album,
                    defaults={
                        "duration": random.randint(180, 300),  # 3–5 นาที
                        "language": "th",
                        "release_date": timezone.now().date(),
                        "is_active": True,
                    },
                )

                if created:
                    # Add random genre
                    song.genres.add(random.choice(list(genre_objs.values())))

                    # 👉 สุ่ม emotion
                    random_emotion = random.choice(list(emotion_objs.values()))
                    SongEmotion.objects.get_or_create(
                        song=song,
                        emotion=random_emotion,
                        defaults={
                            "confidence": round(random.uniform(0.6, 1.0), 2),
                            "source": "seed",
                        },
                    )

                    # Song links
                    SongLink.objects.get_or_create(
                        song=song,
                        platform="youtube",
                        defaults={"url": f"https://youtube.com/watch?v={e}{i}demo"},
                    )
                    SongLink.objects.get_or_create(
                        song=song,
                        platform="spotify",
                        defaults={"url": f"https://open.spotify.com/track/{e}{i}demo"},
                    )

                    song_count += 1

        # -------------------------------
        # 4. Summary
        # -------------------------------
        self.stdout.write(
            self.style.SUCCESS(f"🎉 Seed completed: {song_count} new songs created.")
        )
