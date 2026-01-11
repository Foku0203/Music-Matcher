import os
import json
import django
import sys

# ==========================================
# 1. SETUP DJANGO ENVIRONMENT
# ==========================================

# ใช้ชื่อ core ตามที่คุณตั้งไว้ล่าสุด
PROJECT_NAME = 'core' 

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{PROJECT_NAME}.settings')

try:
    django.setup()
except ModuleNotFoundError:
    import glob
    settings_files = glob.glob("**/settings.py", recursive=True)
    if settings_files:
        folder_name = os.path.dirname(settings_files[0])
        print(f"⚠️ ไม่พบ '{PROJECT_NAME}'... แต่เจอโฟลเดอร์ '{folder_name}' แทน")
        print(f"👉 กรุณาแก้บรรทัดที่ 11 เป็น: PROJECT_NAME = '{folder_name}'")
    else:
        print("❌ หาไฟล์ settings.py ไม่เจอ กรุณาตรวจสอบว่าวางไฟล์ import_songs.py ไว้ถูกที่หรือไม่")
    sys.exit(1)

# Import Models
from matcher.models import Song, Artist, Album, Emotion, SongEmotion

# ==========================================
# 2. IMPORT LOGIC (Updated for handling Nulls)
# ==========================================
def import_data():
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, 'music_data.json') 
    
    if not os.path.exists(file_path):
        print(f"❌ ไม่พบไฟล์: {file_path}")
        return

    print("✅ เชื่อมต่อฐานข้อมูลสำเร็จ... เริ่มอ่านไฟล์ JSON")

    with open(file_path, 'r', encoding='utf-8') as f:
        songs_data = json.load(f)

    count_new = 0
    count_exist = 0

    for index, item in enumerate(songs_data):
        try:
            # --- 1. เตรียมข้อมูล (แก้ใหม่ให้ดัก Null ได้ชัวร์ๆ) ---
            # ใช้ or "..." เพื่อกันค่าที่เป็น None (null ใน JSON) หรือ Empty String
            title = item.get('title') or "Unknown Title"
            artist_name = item.get('artist') or "Unknown Artist"
            album_title = item.get('album') or "Unknown Album"  # <--- ตัวแก้ปัญหาอยู่นี่
            
            # JSON ของคุณส่งมาเป็น "2024-05-09" เราเอาแค่ปี 2024
            year = item.get('year')
            
            # ดึง preview_url จาก object spotify (กัน spotify เป็น null ด้วย)
            spotify_data = item.get('spotify') or {} 
            preview_url = spotify_data.get('preview_url')
            external_id = spotify_data.get('id')

            if not external_id:
                # สร้าง ID ปลอมถ้าไม่มี เพื่อป้องกัน Error
                clean_title = title.replace(" ", "")[:5]
                external_id = f"manual_{index}_{clean_title}"

            # --- 2. จัดการ Artist ---
            artist, _ = Artist.objects.get_or_create(name=artist_name)

            # --- 3. จัดการ Album ---
            # ถ้า cover_url เป็น null ให้ปล่อยว่างไว้
            cover_url = item.get('image_url')
            
            album, _ = Album.objects.get_or_create(
                title=album_title,
                artist=artist,
                defaults={
                    'release_year': year,
                    'cover_url': cover_url
                }
            )

            # --- 4. จัดการ Emotion ---
            emotion_obj = None
            emotion_label = item.get('emotion')
            if emotion_label:
                emotion_obj, _ = Emotion.objects.get_or_create(name=emotion_label.lower())

            # --- 5. สร้าง/อัปเดต Song ---
            song, created = Song.objects.update_or_create(
                external_id=external_id,
                defaults={
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'platform': 'spotify',
                    'lyrics': item.get('lyrics') or '', # กัน lyrics เป็น null
                    'preview_url': preview_url,
                    'is_active': True
                }
            )

            # --- 6. ผูก Emotion ---
            if emotion_obj:
                SongEmotion.objects.get_or_create(
                    song=song,
                    emotion=emotion_obj,
                    defaults={'confidence': 1.0, 'source': 'json_import'}
                )

            if created:
                count_new += 1
            else:
                count_exist += 1
                
        except Exception as e:
            # พิมพ์ Error แบบละเอียดขึ้น
            print(f"❌ ข้ามเพลง '{item.get('title', 'Unknown')}': {e}")
            continue

    print(f"\n✨ เสร็จสิ้น! เพิ่มใหม่: {count_new}, มีอยู่แล้ว: {count_exist}")

if __name__ == "__main__":
    import_data()