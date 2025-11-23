import os
import django
import json
import sys

# Setup Django (ชี้ไปที่ core.settings ตามที่คุณบอก)
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matcher.models import Artist, Album, Song, Emotion, SongEmotion, Genre, SongGenre

def run_import():
    print("🚀 เริ่มนำเข้าข้อมูล (V2 - FER2013 & Genres)...")
    
    try:
        with open('complete_music_db_v2.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            songs_data = data['songs']
    except FileNotFoundError:
        print("❌ ไม่เจอไฟล์ 'complete_music_db_v2.json' (ต้องรัน fetch_fer2013_with_genres.py ก่อน)")
        return

    # 1. สร้าง Emotions ตาม FER2013 (7 อารมณ์)
    print("😊 Creating FER2013 Emotions...")
    fer2013_emotions = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
    emotion_map = {}
    
    for name in fer2013_emotions:
        obj, _ = Emotion.objects.get_or_create(name=name)
        emotion_map[name] = obj

    print("🎵 Importing Songs & Genres...")
    for item in songs_data:
        # Artist
        artist_obj, _ = Artist.objects.get_or_create(name=item['artist_name'])
        
        # Album
        album_obj, _ = Album.objects.get_or_create(
            title=item['album'],
            artist=artist_obj,
            defaults={'release_year': item['release_year'], 'cover_url': item['cover_url']}
        )
        
        # Song
        song_obj, created = Song.objects.get_or_create(
            external_id=item['external_id'],
            platform=item['platform'],
            defaults={
                'title': item['title'],
                'artist': artist_obj,
                'album': album_obj,
                'duration_sec': item['duration_sec'],
                'audio_features': item.get('audio_features'),
                'is_active': True
            }
        )

        # Genres (สร้างและผูกกับเพลง)
        for g_name in item.get('genres', []):
            genre_obj, _ = Genre.objects.get_or_create(name=g_name)
            SongGenre.objects.get_or_create(song=song_obj, genre=genre_obj)

        # Song Emotion (ผูกเพลงกับอารมณ์)
        mood = item.get('mood_label')
        if mood in emotion_map:
            SongEmotion.objects.get_or_create(
                song=song_obj, 
                emotion=emotion_map[mood],
                defaults={'confidence': 0.9, 'source': 'rule_based'}
            )

    print(f"\n✅ เสร็จสิ้น! นำเข้าเพลง {len(songs_data)} เพลง พร้อม Genres และ Emotions เรียบร้อย")

if __name__ == '__main__':
    run_import()