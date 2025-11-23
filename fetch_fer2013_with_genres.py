import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
import time
import random

# ==========================================
# รหัส Spotify 
# ==========================================
CLIENT_ID = 'eb3cda38a49f44ffaf453f1a556476f0'
CLIENT_SECRET = '7b6613c3ecb14e78b031af400f5a6877'

auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

EMOTION_CONFIG = {
    "angry": ["artist:Paper Planes", "artist:Bodyslam", "artist:Cocktail", "artist:Taitosmith", "artist:Lomosonic", "เดือด", "ร็อค", "Metal"],
    "disgust": ["artist:The Yers", "artist:Violette Wautier", "artist:Zom Marie", "เกลียด", "ขยะแขยง", "ไม่รักไม่ต้อง", "Ew"],
    "fear": ["artist:Palmy", "artist:Scrubb", "artist:Anatomy Rabbit", "กลัว", "ซ่อนกลิ่น", "ระแวง", "ผีเสื้อราตรี", "Creepy"],
    "happy": ["artist:Nont Tanont", "artist:Ink Waruntorn", "artist:Bowkylion", "artist:Lipta", "รักแรกพบ", "คลั่งรัก", "Happy"],
    "sad": ["artist:Three Man Down", "artist:Tilly Birds", "artist:Jeff Satur", "artist:Safeplanet", "ฝนตกไหม", "เจ็บจนพอ", "เศร้า"],
    "surprise": ["artist:YOUNGOHM", "artist:MILLI", "artist:F.HERO", "ธาตุทองซาวด์", "ตื่นเต้น", "Wow", "EDM"],
    "neutral": ["artist:Whal & Dolph", "artist:Dept", "artist:Yew", "artist:Landokmai", "ชิล", "เรื่อยๆ", "Study"]
}

def generate_data_with_genres():
    target_per_emotion = 30
    all_songs = []
    artist_ids = set() # เก็บ ID ศิลปินเพื่อไปดึง Genre ทีหลัง
    
    print(f"🚀 เริ่มดึงเพลง 7 อารมณ์ FER2013 + แนวเพลง (Genres)...")
    
    # 1. ดึงเพลงและเก็บ Artist ID
    collected_ids = set()

    for emotion, queries in EMOTION_CONFIG.items():
        print(f"\n🎭 หมวด: {emotion.upper()}...")
        count = 0
        random.shuffle(queries)
        
        for q in queries:
            if count >= target_per_emotion: break
            try:
                results = sp.search(q=q, type='track', limit=20, market='TH')
                for track in results['tracks']['items']:
                    if count >= target_per_emotion: break
                    if track['id'] in collected_ids: continue
                    
                    # เก็บข้อมูลเบื้องต้น
                    song_data = {
                        "title": track['name'],
                        "artist_name": track['artists'][0]['name'],
                        "artist_id": track['artists'][0]['id'], # เอาไว้ดึง Genre
                        "album": track['album']['name'],
                        "release_year": int(track['album']['release_date'][:4]) if track['album']['release_date'] else 2023,
                        "cover_url": track['album']['images'][0]['url'] if track['album']['images'] else "",
                        "duration_sec": int(track['duration_ms'] / 1000),
                        "platform": "spotify",
                        "external_id": track['id'],
                        "mood_label": emotion,
                        "genres": [] # รอเติม
                    }
                    all_songs.append(song_data)
                    collected_ids.add(track['id'])
                    artist_ids.add(song_data['artist_id'])
                    count += 1
            except: pass
            time.sleep(0.5)

    # 2. ดึง Genres ของศิลปิน (Batch Request ทีละ 50 คน เพื่อไม่ให้โดนแบน)
    print(f"\n🎸 กำลังดึงแนวเพลง (Genres) ของศิลปิน {len(artist_ids)} คน...")
    artist_id_list = list(artist_ids)
    artist_genre_map = {}

    for i in range(0, len(artist_id_list), 50):
        chunk = artist_id_list[i:i+50]
        try:
            artists_info = sp.artists(chunk)
            for artist in artists_info['artists']:
                # เก็บ Genre ตัวแรก (ถ้ามี) หรือระบุเป็น Pop ถ้าหาไม่เจอ
                genres = artist.get('genres', [])
                artist_genre_map[artist['id']] = genres
        except Exception as e:
            print(f"⚠️ Error fetching artists: {e}")
        time.sleep(1)

    # 3. เอา Genre ยัดกลับใส่เพลง
    final_db_ready = []
    for song in all_songs:
        # ใส่ Genre
        art_id = song['artist_id']
        if art_id in artist_genre_map and artist_genre_map[art_id]:
            song['genres'] = artist_genre_map[art_id]
        else:
            song['genres'] = ["Thai Pop"] # ค่า Default
        
        # สร้าง Audio Features ปลอม (ตาม FER2013) เพื่อให้ระบบทำงานได้
        mood = song['mood_label']
        if mood == 'angry': val, en = (0.1, 0.4), (0.8, 1.0)
        elif mood == 'disgust': val, en = (0.2, 0.4), (0.5, 0.7)
        elif mood == 'fear': val, en = (0.1, 0.3), (0.3, 0.6)
        elif mood == 'happy': val, en = (0.7, 1.0), (0.6, 0.9)
        elif mood == 'sad': val, en = (0.0, 0.3), (0.1, 0.4)
        elif mood == 'surprise': val, en = (0.6, 0.9), (0.8, 1.0)
        else: val, en = (0.4, 0.6), (0.4, 0.6) # neutral
        
        song['audio_features'] = {
            "valence": round(random.uniform(*val), 3),
            "energy": round(random.uniform(*en), 3),
            "tempo": round(random.uniform(80, 140), 2),
            "danceability": round(random.uniform(0.4, 0.8), 3)
        }
        final_db_ready.append(song)

    # บันทึกไฟล์
    filename = 'complete_music_db_v2.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({"songs": final_db_ready}, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ เสร็จสมบูรณ์! ได้ไฟล์ '{filename}'")
    print(f"   - จำนวนเพลง: {len(final_db_ready)}")
    print(f"   - อารมณ์: ครบ 7 แบบ FER2013")
    print(f"   - Genres: มาครบ!")

if __name__ == "__main__":
    generate_data_with_genres()