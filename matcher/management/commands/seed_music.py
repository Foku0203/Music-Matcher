from django.core.management.base import BaseCommand
from matcher.models import Artist, Album, Song, Genre, SongGenre

class Command(BaseCommand):
    help = "Seed minimal music data"

    def handle(self, *args, **kwargs):
        artist_names = ["Artist A", "Artist B", "Artist C"]
        genre_names = ["Pop", "Rock", "Hip Hop"]

        artists = [Artist.objects.get_or_create(name=name)[0] for name in artist_names]
        genres = [Genre.objects.get_or_create(name=name)[0] for name in genre_names]

        album_a1 = Album.objects.get_or_create(artist=artists[0], title="Album A1", year=2020)[0]
        album_b1 = Album.objects.get_or_create(artist=artists[1], title="Album B1", year=2021)[0]

        song_a1 = Song.objects.get_or_create(title="Song A1", artist=artists[0], album=album_a1)[0]
        song_b1 = Song.objects.get_or_create(title="Song B1", artist=artists[1], album=album_b1)[0]

        SongGenre.objects.get_or_create(song=song_a1, genre=genres[0])
        SongGenre.objects.get_or_create(song=song_b1, genre=genres[1])

        self.stdout.write(self.style.SUCCESS("Seeded music data"))