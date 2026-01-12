import json
import random

# ==========================================
# ⚙️ ตั้งค่า
# ==========================================
INPUT_FILE = 'thai_songs_labeled_final.json' # ไฟล์จากขั้นตอนที่แล้ว
OUTPUT_FILE = 'thai_songs_balanced_200.json' # ไฟล์ผลลัพธ์ที่จะเอาไปเทรนจริง
TARGET_COUNT = 50  # ต้องการอารมณ์ละกี่เพลง

def balance_dataset():
    try:
        print(f"📂 กำลังอ่านไฟล์ {INPUT_FILE} ...")
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 1. แยกตะกร้าอารมณ์
        buckets = {
            'happy': [],
            'sad': [],
            'angry': [],
            'neutral': []
        }
        
        for song in data:
            emotion = song.get('emotion')
            if emotion in buckets:
                buckets[emotion].append(song)
        
        # 2. คัดเลือก (Sampling)
        final_dataset = []
        print("\n📊 สรุปยอดเพลงที่คัดมา:")
        
        for emotion, songs in buckets.items():
            total_available = len(songs)
            
            # ถ้าเพลงมีเยอะกว่า 50 -> สุ่มมา 50
            if total_available >= TARGET_COUNT:
                selected = random.sample(songs, TARGET_COUNT)
                count_msg = f"✅ ครบ {TARGET_COUNT}"
            # ถ้าเพลงมีน้อยกว่า 50 -> เอามาทั้งหมดที่มี
            else:
                selected = songs
                count_msg = f"⚠️ มีแค่ {total_available} (เอามาหมด)"
            
            final_dataset.extend(selected)
            print(f"   - {emotion.capitalize()}: {count_msg} เพลง (จากทั้งหมด {total_available})")

        # 3. สลับลำดับเพลง (Shuffle) ไม่ให้มันเรียง Happy ติดกัน 50 เพลง
        random.shuffle(final_dataset)
        
        # 4. บันทึก
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_dataset, f, ensure_ascii=False, indent=4)
            
        print(f"\n💾 บันทึกไฟล์เสร็จเรียบร้อย: {OUTPUT_FILE}")
        print(f"🔥 จำนวนเพลงทั้งหมดในไฟล์นี้: {len(final_dataset)} เพลง")
        print("👉 พร้อมเอาไปเข้าโมเดลเทรนได้เลย!")

    except FileNotFoundError:
        print(f"❌ หาไฟล์ {INPUT_FILE} ไม่เจอ! (คุณรันสคริปต์แก้ Label รอบที่แล้วหรือยัง?)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    balance_dataset()