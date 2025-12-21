import json
import time
import random
import sys

# ตรวจสอบไลบรารี
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    print("❌ Error: ยังไม่พบไลบรารี 'spotipy'")
    print("👉 วิธีแก้: พิมพ์คำสั่ง 'pip install spotipy' ใน Terminal")
    sys.exit()

# ==========================================
# 1. ตั้งค่า Spotify API (ใช้ ID เดิมของคุณ)
# ==========================================
# ⚠️ อย่าลืมไป Reset Secret หลังโปรเจกต์จบนะ
SPOTIPY_CLIENT_ID = 'eb3cda38a49f44ffaf453f1a556476f0'
SPOTIPY_CLIENT_SECRET = '7b6613c3ecb14e78b031af400f5a6877'

print("🔄 กำลังเชื่อมต่อ Spotify...")
try:
    auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    print("✅ เชื่อมต่อสำเร็จ!")
except Exception as e:
    print(f"❌ เชื่อมต่อไม่สำเร็จ: {e}")
    sys.exit()

# ==========================================
# 2. ฟังก์ชันค้นหา
# ==========================================
def get_spotify_data(artist, title):
    try:
        # รอบ 1: ค้นหาแบบระบุ track/artist เป๊ะๆ
        q = f"track:{title} artist:{artist}"
        results = sp.search(q=q, type='track', limit=1)
        items = results['tracks']['items']
        
        # รอบ 2: ถ้าไม่เจอ ลองค้นแบบกว้าง (เผื่อชื่อเพลงใน Genius ไม่ตรงกับ Spotify)
        if not items:
            q_wide = f"{title} {artist}"
            results = sp.search(q=q_wide, type='track', limit=1)
            items = results['tracks']['items']

        if items:
            track = items[0]
            track_id = track['id']
            # สร้าง Embed Link แบบมาตรฐานสำหรับแปะเว็บ
            embed_url = f"https://open.spotify.com/embed/track/{track_id}?utm_source=generator"
            
            return {
                "id": track_id,
                "name_on_spotify": track['name'],
                "artist_on_spotify": track['artists'][0]['name'],
                "link": track['external_urls']['spotify'],
                "embed": embed_url,
                "preview_url": track['preview_url'] # เสียงตัวอย่าง 30 วิ (ถ้ามี)
            }
    except Exception as e:
        print(f"   ⚠️ Error Searching: {e}")
    return None

# ==========================================
# 3. เริ่มทำงาน
# ==========================================
INPUT_FILE = 'lyrics.json'  # << ไฟล์ต้นฉบับของคุณ
OUTPUT_FILE = 'thai_songs_spotify_only.json' # << ไฟล์ที่จะได้ออกมา

# โหลดไฟล์
try:
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        songs = json.load(f)
    print(f"📂 อ่านไฟล์ '{INPUT_FILE}' สำเร็จ! พบทั้งหมด {len(songs)} เพลง")
except FileNotFoundError:
    print(f"❌ ไม่พบไฟล์ {INPUT_FILE} กรุณาตรวจสอบว่าวางไฟล์ json ไว้ที่เดียวกับโค้ดนี้ไหม")
    sys.exit()

print("🚀 เริ่มค้นหาเพลงบน Spotify...")

found_count = 0
for i, song in enumerate(songs):
    # ถ้าเพลงไหนมีข้อมูลอยู่แล้ว ให้ข้าม (เผื่อรันรอบ 2)
    if 'spotify' in song:
        continue

    print(f"[{i+1}/{len(songs)}] 🔍 {song.get('title')} - {song.get('artist')}")
    
    sp_data = get_spotify_data(song.get('artist'), song.get('title'))
    
    if sp_data:
        song['spotify'] = sp_data
        found_count += 1
        print(f"   ✅ เจอแล้ว! -> {sp_data['name_on_spotify']}")
    else:
        print("   ⚪ ไม่พบ")

    # Save ทุกๆ 10 เพลง (กันไฟดับ)
    if (i + 1) % 10 == 0:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(songs, f, ensure_ascii=False, indent=4)
        print("   💾 บันทึก checkpoint...")

    # พักนิดนึง เดี๋ยว Spotify ว่าเอา
    time.sleep(0.5)

# Save รอบสุดท้าย
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(songs, f, ensure_ascii=False, indent=4)

print("\n" + "="*30)
print(f"🎉 เสร็จสิ้นภารกิจ!")
print(f"✅ หาเจอทั้งหมด: {found_count} เพลง")
print(f"📂 ได้ไฟล์ใหม่ชื่อ: {OUTPUT_FILE}")
print("👉 (ให้เอาไฟล์นี้ไปใช้รัน training ต่อครับ)")