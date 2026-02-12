import os
import sys
import json
import django
from datetime import datetime

# ==========================================
# ⚙️ ตั้งค่า DJANGO ENVIRONMENT
# ==========================================
# ⚠️ ตรวจสอบชื่อโปรเจกต์ของคุณใน manage.py ให้ตรงกัน (เช่น music_matcher.settings)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 

# Setup Django
django.setup()

# Import Models
from django.db import transaction
from matcher.models import Song, Artist, Album

def import_data():
    json_file = 'songdata.json'
    
    if not os.path.exists(json_file):
        print(f"❌ ไม่พบไฟล์ {json_file}")
        return

    print("🚀 กำลังอ่านไฟล์ JSON...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    print(f"📂 พบเพลงทั้งหมด {total} เพลง. กำลังนำเข้า Database...")

    created_count = 0
    updated_count = 0

    try:
        with transaction.atomic():
            for i, item in enumerate(data, 1):
                # 1. จัดการ Artist
                artist_name = item.get('artist', 'Unknown Artist')
                # ใช้ get_or_create เพื่อกัน duplicate artist
                artist, _ = Artist.objects.get_or_create(name=artist_name)

                # 2. จัดการ Album
                album_title = item.get('album')
                album = None
                if album_title:
                    album, _ = Album.objects.get_or_create(
                        title=album_title,
                        artist=artist
                    )

                # 3. เตรียมข้อมูล
                spotify_data = item.get('spotify', {}) or {}
                audio_features = item.get('audio_features', {}) or {}
                
                # ดึง Spotify ID มาเช็คก่อน
                sid = spotify_data.get('id')
                
                # แปลงวันที่
                release_date_str = item.get('release_date')
                release_date = None
                if release_date_str:
                    try:
                        release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass

                # เตรียม Dict ข้อมูลที่จะบันทึก
                defaults_data = {
                    'title': item.get('title'), # Title ย้ายมาใน defaults
                    'artist': artist,
                    'album': album,
                    'release_date': release_date,
                    'lyrics': item.get('lyrics', ''),
                    'image_url': item.get('image_url', ''),
                    'genius_url': item.get('url', ''),
                    'json_mood': item.get('mood', ''),
                    'json_genre': item.get('genre', ''),
                    'spotify_link': spotify_data.get('link'),
                    'spotify_preview_url': spotify_data.get('preview_url'),
                    'spotify_embed_url': spotify_data.get('embed'),
                    'valence': audio_features.get('valence', 0.5),
                    'energy': audio_features.get('energy', 0.5),
                    'tempo': audio_features.get('tempo', 120.0),
                    'danceability': audio_features.get('danceability', 0.5),
                }

                # 4. สร้างหรืออัปเดต Song (แก้ Logic ตรงนี้)
                if sid:
                    # ✅ Case A: มี Spotify ID -> ใช้ ID เป็นตัวยืนยันตัวตน (Lookup)
                    # ถ้ามี ID นี้ในระบบแล้ว ให้อัปเดตข้อมูลอื่นแทนการสร้างใหม่
                    song, created = Song.objects.update_or_create(
                        spotify_id=sid,
                        defaults=defaults_data
                    )
                else:
                    # ✅ Case B: ไม่มี Spotify ID -> ใช้ ชื่อเพลง + ศิลปิน เป็นตัวยืนยัน
                    song, created = Song.objects.update_or_create(
                        title=item.get('title'),
                        artist=artist,
                        defaults=defaults_data
                    )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

                if i % 10 == 0:
                    print(f"   ⏳ Processed {i}/{total} songs...")

        print("-" * 30)
        print(f"✅ เสร็จสมบูรณ์!")
        print(f"🆕 เพิ่มใหม่: {created_count} เพลง")
        print(f"🔄 อัปเดตเดิม: {updated_count} เพลง")
        print("-" * 30)

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        # ปริ้นท์บอกด้วยว่าพังที่เพลงไหน
        print(f"   (Error at Item index {i}: {item.get('title', 'Unknown Title')})")

if __name__ == '__main__':
    import_data()