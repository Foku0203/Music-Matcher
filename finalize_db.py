# finalize_db.py
import json
import datetime

try:
    # อ่านไฟล์เพลงดิบ
    with open('thai_songs_fer2013.json', 'r', encoding='utf-8') as f:
        source_data = json.load(f)
        songs_raw = source_data['songs']
except FileNotFoundError:
    print("❌ ไม่เจอไฟล์ thai_songs_fer2013.json (ต้องไปรันสคริปต์หาเพลงก่อนนะครับ)")
    exit()

# Map ชื่ออารมณ์เป็น ID
EMOTION_MAP = {"happy": 1, "sad": 2, "angry": 3, "calm": 4, "neutral": 5, "surprise": 6, "energetic": 7, "disgust": 3, "fear": 2}

artists_db = []
albums_db = []
songs_db = []
song_emotions_db = []

artist_map = {} 
album_map = {}  

artist_id_counter = 1
album_id_counter = 1
song_id_counter = 1

print(f"⚙️ กำลังแปลงข้อมูล {len(songs_raw)} เพลง...")

for track in songs_raw:
    # 1. Artist
    if track['artist'] not in artist_map:
        artists_db.append({"artist_id": artist_id_counter, "name": track['artist']})
        artist_map[track['artist']] = artist_id_counter
        artist_id_counter += 1
    curr_artist_id = artist_map[track['artist']]

    # 2. Album
    if track['album'] not in album_map:
        albums_db.append({
            "album_id": album_id_counter, "artist_id": curr_artist_id, 
            "title": track['album'], "release_year": track['release_year'], "cover_url": track['cover_url']
        })
        album_map[track['album']] = album_id_counter
        album_id_counter += 1
    curr_album_id = album_map[track['album']]

    # 3. Song
    songs_db.append({
        "song_id": song_id_counter, "album_id": curr_album_id, "artist_id": curr_artist_id,
        "title": track['title'], "duration_sec": track['duration_sec'],
        "platform": track['platform'], "external_id": track['external_id'],
        "audio_features": track['audio_features'], "is_active": True,
        "created_at": datetime.datetime.now().isoformat()
    })

    # 4. Emotion
    if track['mood_label'] in EMOTION_MAP:
        song_emotions_db.append({
            "song_id": song_id_counter, "emotion_id": EMOTION_MAP[track['mood_label']],
            "confidence": 0.85, "source": "rule_based"
        })
    song_id_counter += 1

# บันทึกเป็นไฟล์ final
final_db = {"artists": artists_db, "albums": albums_db, "songs": songs_db, "song_emotions": song_emotions_db}
with open('complete_music_db.json', 'w', encoding='utf-8') as f:
    json.dump(final_db, f, ensure_ascii=False, indent=4)

print("✅ ได้ไฟล์ complete_music_db.json แล้ว! พร้อม Import!")