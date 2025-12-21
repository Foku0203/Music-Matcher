import lyricsgenius
import json
import time
import os
import sys

# ==========================================
# 1. ตั้งค่า API
# ==========================================
# !!! ใส่ Token ของคุณตรงนี้ !!!
GENIUS_ACCESS_TOKEN = "mrF4wm7h9-x2lcRMbdur8zpcFidhjGqHJIiMjASY8W7prU2B3P0UE612URlFEPZ7"

# ตั้งค่า Timeout ให้นานขึ้น และ Retry เยอะขึ้น
genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN, timeout=60, retries=10)
genius.verbose = False       
genius.remove_section_headers = True 
genius.skip_non_songs = True 
genius.excluded_terms = ["(Remix)", "(Live)", "(Demo)", "(Instrumental)"]

# ==========================================
# 2. รายชื่อศิลปิน
# ==========================================
thai_artists_list = [
    "Bodyslam", "Big Ass", "Potato", "Cocktail", "Paradox", "Labanoon", 
    "Klear", "Retrospect", "Sweet Mullet", "The Mousses", "25hours", 
    "Lomosonic", "Slot Machine", "Getsunova", "Palmy", "Num Kala", 
    "Paper Planes", "Joey Phuwasit", "Taitosmith", "Three Man Down", "Tilly Birds",
    "Zeal", "Silly Fools", "Clash", "Ebola", "The Yers", "Bomb At Track",
    "Bowkylion", "The Toys", "Ink Waruntorn", "Polycat", "Violette Wautier", 
    "Nont Tanont", "Jeff Satur", "Billkin", "PP Krit", "4EVE", "ATLAS", "Pixxie",
    "F.HERO", "Youngohm", "URBOYTJ", "Illslick", "Twopee Southside", 
    "1MILL", "SPRITE", "OG-ANIC", "Lazyloxy", "Milli", "Saran"
]

MIN_YEAR = 2012
SONGS_PER_ARTIST = 100
FILENAME = 'thai_songs_final_fixed.json'

def scrape_genius_super_safe():
    collected_songs = []
    
    # โหลดไฟล์เดิมถ้ามี (Resume)
    if os.path.exists(FILENAME):
        try:
            with open(FILENAME, 'r', encoding='utf-8') as f:
                collected_songs = json.load(f)
            print(f"Resuming... Found {len(collected_songs)} existing songs.")
        except:
            pass

    # สร้าง Set เก็บชื่อเพลง+ศิลปิน เพื่อกันซ้ำ
    existing_keys = set(f"{s.get('title')}_{s.get('artist')}" for s in collected_songs)

    print(f"Starting scrape for {len(thai_artists_list)} artists...")

    for artist_idx, artist_name in enumerate(thai_artists_list):
        # ใช้ print ภาษาอังกฤษล้วน
        print(f"\n[{artist_idx + 1}/{len(thai_artists_list)}] Processing Artist: {artist_name}")
        
        try:
            artist = genius.search_artist(artist_name, max_songs=SONGS_PER_ARTIST, sort="popularity")
            
            if not artist:
                print(f" - Artist not found: {artist_name}")
                continue

            added_count = 0
            for song in artist.songs:
                # !!! จุดสำคัญ: แปลงเป็น Dict ก่อนเรียกใช้ เพื่อป้องกัน AttributeError !!!
                s_dict = song.to_dict()
                
                title = s_dict.get('title', 'Unknown')
                artist_val = s_dict.get('artist_names', artist_name) # บางที key คือ artist_names
                
                unique_key = f"{title}_{artist_val}"
                if unique_key in existing_keys:
                    continue

                # --- 1. หาปีแบบปลอดภัยสุดๆ (Safe Parsing) ---
                song_year = None
                
                # ลองหาจาก release_date (รูปแบบ "2023-11-25")
                r_date = s_dict.get('release_date')
                if r_date:
                    try:
                        song_year = int(str(r_date).split('-')[0])
                    except:
                        pass
                
                # ถ้าไม่มี ให้ลองหาจาก field 'year' ตรงๆ
                if not song_year and s_dict.get('release_date_components'):
                     try:
                         song_year = s_dict['release_date_components'].get('year')
                     except:
                         pass

                # --- 2. เช็คเงื่อนไขปี ---
                if song_year and song_year >= MIN_YEAR:
                    
                    # เก็บข้อมูลลง List
                    final_data = {
                        "id": s_dict.get('id'),
                        "title": title,
                        "artist": artist_val,
                        "album": s_dict.get('album', {}).get('name') if s_dict.get('album') else None,
                        "year": song_year,
                        "release_date": r_date,
                        "lyrics": s_dict.get('lyrics'),
                        "image_url": s_dict.get('song_art_image_url'),
                        "url": s_dict.get('url'),
                        "stats_pageviews": s_dict.get('stats', {}).get('pageviews', 0)
                    }
                    
                    collected_songs.append(final_data)
                    existing_keys.add(unique_key)
                    added_count += 1
                    
                    # ปริ้นท์แค่ ID (ปลอดภัยกับ Windows จอดำ)
                    print(f"   + Saved ID: {s_dict.get('id')} (Year: {song_year})")

            # Save ทุกครั้งที่จบ 1 ศิลปิน
            with open(FILENAME, 'w', encoding='utf-8') as f:
                json.dump(collected_songs, f, ensure_ascii=False, indent=4)
            
            print(f"   >> Done with {artist_name}. Added {added_count} songs.")

        except Exception as e:
            # ดักจับ Error ทุกอย่างแล้วข้ามไป ไม่ให้โปรแกรมหยุด
            print(f"   !!! Error with {artist_name}: {str(e)[:50]}...")
            time.sleep(5)
            continue

    print(f"\nCompleted! Total songs collected: {len(collected_songs)}")
    print(f"File saved to: {FILENAME}")

if __name__ == "__main__":
    scrape_genius_super_safe()