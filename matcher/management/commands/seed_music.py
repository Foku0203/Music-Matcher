from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from matcher.models import Artist, Album, Song, Genre, SongGenre, Emotion, SongEmotion
import csv
from pathlib import Path

class Command(BaseCommand):
    help = "Seed minimal music data for demo, or import from CSV via --csv <path>"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Path to CSV file exported from your sheet to import songs/artists/genres/emotions",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = options.get("csv")
        if csv_path:
            self._import_from_csv(csv_path)
        else:
            self._seed_demo()

    def _seed_demo(self):
        User = get_user_model()

        # ผู้ใช้ทดสอบ
        User.objects.get_or_create(
            email="demo@example.com",
            defaults={"username": "demo", "password": "demo1234"}
        )
        # หมายเหตุ: ถ้าต้องการ hash password ให้ใช้ create_user
        if not User.objects.filter(username="demo").exists():
            User.objects.create_user(
                username="demo", email="demo@example.com", password="demo1234"
            )

        # ศิลปิน/อัลบั้ม/เพลง
        a1, _ = Artist.objects.get_or_create(name="Artist A")
        alb1, _ = Album.objects.get_or_create(artist=a1, title="Album A1", release_year=2020)
        s1, _ = Song.objects.get_or_create(
            artist=a1, album=alb1, title="Happy Day",
            defaults={"platform": "youtube", "external_id": "yt001", "duration_sec": 210}
        )
        s2, _ = Song.objects.get_or_create(
            artist=a1, album=alb1, title="Blue Night",
            defaults={"platform": "spotify", "external_id": "sp002", "duration_sec": 190}
        )

        # แนวเพลง
        g_pop, _ = Genre.objects.get_or_create(name="Pop")
        g_ballad, _ = Genre.objects.get_or_create(name="Ballad")
        SongGenre.objects.get_or_create(song=s1, genre=g_pop)
        SongGenre.objects.get_or_create(song=s2, genre=g_ballad)

        # อารมณ์
        e_happy, _ = Emotion.objects.get_or_create(name="happy")
        e_sad, _ = Emotion.objects.get_or_create(name="sad")
        SongEmotion.objects.get_or_create(song=s1, emotion=e_happy, defaults={"confidence": 0.92, "source": "ml"})
        SongEmotion.objects.get_or_create(song=s2, emotion=e_sad, defaults={"confidence": 0.88, "source": "ml"})

        self.stdout.write(self.style.SUCCESS("Seeded demo data."))

    def _import_from_csv(self, csv_path: str):
        path = Path(csv_path)
        if not path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        """
        คอลัมน์ที่รองรับ (ตัวอย่าง แนะนำให้ตั้งหัวตารางแบบนี้):
        artist,album,release_year,song_title,platform,external_id,duration_sec,genres,emotions,emotion_confidences,emotion_source
        - genres: คั่นด้วย ‘|’ เช่น Pop|Ballad
        - emotions: คั่นด้วย ‘|’ เช่น happy|sad
        - emotion_confidences: คั่นด้วย ‘|’ ให้ตรงลำดับ เช่น 0.92|0.88
        - emotion_source: แหล่งที่มา เช่น ml หรือ manual (ไม่บังคับ)
        """

        inserted = 0
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=1):
                artist_name = (row.get("artist") or "").strip()
                album_title = (row.get("album") or "").strip()
                release_year = row.get("release_year")
                song_title = (row.get("song_title") or "").strip()
                platform = (row.get("platform") or "").strip() or "unknown"
                external_id = (row.get("external_id") or "").strip()
                duration_sec = row.get("duration_sec")
                genres = (row.get("genres") or "").split("|")
                emotions = (row.get("emotions") or "").split("|")
                confs = (row.get("emotion_confidences") or "").split("|")
                e_source = (row.get("emotion_source") or "sheet").strip()

                if not artist_name or not song_title:
                    self.stdout.write(self.style.WARNING(f"Row {i}: missing artist or song_title, skipped"))
                    continue

                try:
                    release_year = int(release_year) if release_year else None
                except ValueError:
                    release_year = None

                try:
                    duration_sec = int(duration_sec) if duration_sec else None
                except ValueError:
                    duration_sec = None

                a, _ = Artist.objects.get_or_create(name=artist_name)
                alb, _ = Album.objects.get_or_create(artist=a, title=album_title or f"{artist_name} - Single",
                                                     defaults={"release_year": release_year})
                song, created = Song.objects.get_or_create(
                    artist=a, album=alb, title=song_title,
                    defaults={"platform": platform, "external_id": external_id, "duration_sec": duration_sec}
                )
                if created:
                    inserted += 1

                # genres
                for g in [g.strip() for g in genres if g.strip()]:
                    g_obj, _ = Genre.objects.get_or_create(name=g)
                    SongGenre.objects.get_or_create(song=song, genre=g_obj)

                # emotions + confidence
                for idx, emo in enumerate([e.strip() for e in emotions if e.strip()]):
                    e_obj, _ = Emotion.objects.get_or_create(name=emo)
                    conf = None
                    if idx < len(confs):
                        try:
                            conf = float(confs[idx])
                        except ValueError:
                            conf = None
                    SongEmotion.objects.get_or_create(
                        song=song, emotion=e_obj,
                        defaults={"confidence": conf, "source": e_source}
                    )

        self.stdout.write(self.style.SUCCESS(f"Imported from CSV: inserted {inserted} new songs"))
