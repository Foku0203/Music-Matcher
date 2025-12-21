import json
import psycopg2
from psycopg2 import extras
import os

# 1. ตั้งค่าการเชื่อมต่อฐานข้อมูล
DB_CONFIG = {
    "host": "localhost",
    "database": "mmdb",
    "user": "postgres",
    "password": "123456",
    "port": "5432"
}

def import_data():
    conn = None
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_path, 'music_data.json')
        
        if not os.path.exists(file_path):
            print(f"❌ ไม่พบไฟล์: {file_path}")
            return

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✅ เชื่อมต่อฐานข้อมูลสำเร็จ")

        with open(file_path, 'r', encoding='utf-8') as f:
            songs_data = json.load(f)
        
        print(f"🔄 กำลังนำเข้าข้อมูลจำนวน {len(songs_data)} รายการ...")

        for index, item in enumerate(songs_data):
            # --- 1. เตรียมข้อมูลพื้นฐาน ---
            title = item.get('title') or "Unknown Title"
            artist_name = item.get('artist') or "Unknown Artist"
            
            # แก้ Unknow -> Unknown และเช็ค string ว่าง
            album_title = item.get('album')
            if not album_title or not album_title.strip():
                album_title = "Unknown Album"
            
            # แปลงปีให้ปลอดภัย (ถ้าไม่ใช่ตัวเลข ให้เป็น None)
            year = item.get('year')
            if year and str(year).isdigit():
                year = int(year)
            else:
                year = None

            lyrics = item.get('lyrics')
            cover_url = item.get('image_url')
            emotion_label = item.get('label') 

            # จัดการ External ID
            spotify_info = item.get('spotify')
            external_id = None
            if isinstance(spotify_info, dict):
                external_id = spotify_info.get('id')
            
            if not external_id:
                external_id = f"manual_{index}_{title[:5]}" # เพิ่ม title นิดหน่อยกันซ้ำ

            # --- 2. จัดการข้อมูลศิลปิน (Artists) ---
            # ต้องมี UNIQUE(name) ในตาราง artists
            cur.execute(
                """
                INSERT INTO artists (name) 
                VALUES (%s) 
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name 
                RETURNING artist_id
                """,
                (artist_name,)
            )
            artist_id = cur.fetchone()[0]

            # --- 3. จัดการข้อมูลอัลบั้ม (Albums) ---
            # ต้องมี UNIQUE(artist_id, title) ในตาราง albums
            cur.execute(
                """
                INSERT INTO albums (artist_id, title, release_year, cover_url) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (artist_id, title) 
                DO UPDATE SET release_year = EXCLUDED.release_year, cover_url = EXCLUDED.cover_url
                RETURNING album_id
                """,
                (artist_id, album_title, year, cover_url)
            )
            album_id = cur.fetchone()[0]

            # --- 4. เพิ่มข้อมูลเพลง (Songs) ---
            # ต้องมี UNIQUE(external_id) ในตาราง songs
            cur.execute(
                """
                INSERT INTO songs (album_id, artist_id, title, platform, external_id, lyrics)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (external_id) 
                DO UPDATE SET lyrics = EXCLUDED.lyrics, title = EXCLUDED.title
                RETURNING song_id
                """,
                (album_id, artist_id, title, 'spotify', external_id, lyrics)
            )
            song_id = cur.fetchone()[0]

            # --- 5. จัดการข้อมูลอารมณ์ (Emotions) ---
            if emotion_label:
                # ต้องมี UNIQUE(name) ในตาราง emotions
                cur.execute(
                    """
                    INSERT INTO emotions (name) 
                    VALUES (%s) 
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name 
                    RETURNING emotion_id
                    """,
                    (emotion_label.lower(),)
                )
                emotion_id = cur.fetchone()[0]

                # ต้องมี UNIQUE(song_id, emotion_id) ในตาราง song_emotions
                cur.execute(
                    """
                    INSERT INTO song_emotions (song_id, emotion_id, confidence, source)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (song_id, emotion_id) DO NOTHING
                    """,
                    (song_id, emotion_id, 1.000, 'manual_import')
                )

        conn.commit()
        print(f"✨ สำเร็จ! นำเข้าข้อมูล {len(songs_data)} เพลงเรียบร้อยแล้ว")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    import_data()