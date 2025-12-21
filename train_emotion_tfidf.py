import json
import re
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb
from pythainlp import word_tokenize
from pythainlp.util import normalize
from pythainlp.corpus import thai_stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

# ==========================================
# 🧠 CLASS: Music Emotion Engine
# ==========================================
class ThaiMusicEmotionClassifier:
    def __init__(self, input_file, output_file):
        self.input_file = input_file
        self.output_file = output_file
        self.df = None
        self.pipeline = None
        self.label_encoder = None
        
        # 1. คลังคำศัพท์สำหรับ Auto-Labeling (มีน้ำหนักคะแนน)
        self.keywords = {
            'happy': { # สนุก, ตื่นเต้น, รักสมหวัง
                'สนุก': 2, 'สุข': 2, 'ยิ้ม': 1, 'หัวเราะ': 2, 'แดนซ์': 3, 'มันส์': 2, 
                'สวยงาม': 1, 'รัก': 1, 'สดใส': 2, 'ตื่นเต้น': 2, 'baby': 1, 'party': 3,
                'หมอลำ': 2, 'โจ๊ะ': 3, 'สวรรค์': 1, 'งดงาม': 1, 'ร่าเริง': 2
            },
            'sad': { # เศร้า, อกหัก, ผิดหวัง, กลัว
                'เจ็บ': 2, 'ช้ำ': 2, 'น้ำตา': 3, 'ร้องไห้': 3, 'จากลา': 2, 'ทิ้ง': 2, 
                'เหงา': 2, 'เดียวดาย': 2, 'เสียใจ': 2, 'ตาย': 3, 'ทรมาน': 3, 'ผิดหวัง': 2,
                'แตกสลาย': 3, 'ลืม': 1, 'เพ้อ': 1, 'กอด': 1, 'ขอโทษ': 2, 'กลัว': 2, 'กังวล': 2
            },
            'angry': { # โกรธ, เกลียด, รุนแรง
                'เกลียด': 3, 'โกรธ': 2, 'ฆ่า': 3, 'เลว': 3, 'ทนไม่ไหว': 2, 'พัง': 2, 
                'ด่า': 2, 'รำคาญ': 2, 'ไปตาย': 3, 'ขยะ': 3, 'เสือก': 3, 'fuck': 3, 
                'shit': 3, 'damn': 2, 'สันดาน': 3, 'บ้า': 2, 'เดือด': 2
            },
            'neutral': { # เฉยๆ, สบายๆ
                'เรื่อยๆ': 2, 'สบาย': 2, 'ชิล': 2, 'ล่องลอย': 2, 'พักผ่อน': 2, 'สายลม': 1, 
                'ธรรมดา': 1, 'กาแฟ': 2, 'หนังสือ': 1, 'ว่างเปล่า': 1, 'ลมหายใจ': 1, 'เรื่อยเปื่อย': 2
            }
        }

    # --- Preprocessing Tools ---
    def _clean_text(self, text):
        if not isinstance(text, str): return ""
        text = normalize(text) # แก้สระลอย
        text = re.sub(r'http\S+', '', text) # ลบ URL
        text = re.sub(r'\d+', '', text) # ลบตัวเลข
        return text

    def _tokenizer(self, text):
        # ตัดคำด้วย PyThaiNLP + ลบ Stopwords
        text = self._clean_text(text)
        tokens = word_tokenize(text, engine='newmm', keep_whitespace=False)
        return [t for t in tokens if t not in thai_stopwords() and len(t) > 1]

    # --- Core Logic ---
    def auto_label(self):
        print("🏷️  กำลังติดป้ายอารมณ์ (Auto-Labeling)...")
        
        def score_emotion(text):
            if not isinstance(text, str): return 'neutral'
            scores = {k: 0 for k in self.keywords}
            
            for mood, word_dict in self.keywords.items():
                for word, weight in word_dict.items():
                    if word in text:
                        scores[mood] += weight
            
            # ถ้าคะแนนเป็น 0 หมด หรือคะแนนเท่ากัน ให้เป็น neutral
            if sum(scores.values()) == 0: return 'neutral'
            return max(scores, key=scores.get)

        self.df['emotion'] = self.df['lyrics'].apply(score_emotion)
        print("📊 สัดส่วนอารมณ์เพลง:\n", self.df['emotion'].value_counts())

    def build_and_train(self):
        print("\n🚀 กำลังสร้างโมเดล (Hybrid Feature Extraction)...")
        
        # 1. Word-Level Feature (เข้าใจความหมายคำ)
        word_tfidf = TfidfVectorizer(tokenizer=self._tokenizer, ngram_range=(1, 2), max_features=2000)
        
        # 2. Char-Level Feature (เข้าใจแพทเทิร์นตัวอักษร - แก้คำผิด/คำวิบัติ)
        char_tfidf = TfidfVectorizer(analyzer='char', ngram_range=(3, 5), max_features=3000)
        
        # รวมพลัง 2 Features
        combined_features = FeatureUnion([
            ('word', word_tfidf),
            ('char', char_tfidf)
        ])
        
        # XGBoost Classifier
        clf = xgb.XGBClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            objective='multi:softprob', eval_metric='mlogloss', random_state=42
        )
        
        self.pipeline = Pipeline([('features', combined_features), ('clf', clf)])
        
        # Prepare Data
        X = self.df['lyrics'].fillna("")
        self.label_encoder = LabelEncoder()
        y = self.label_encoder.fit_transform(self.df['emotion'])
        
        # Train
        self.pipeline.fit(X, y)
        print("🎉 เทรนโมเดลเสร็จสมบูรณ์!")
        
        # Evaluate (วัดผลตัวเองทันที)
        accuracy = self.pipeline.score(X, y)
        print(f"🏆 Model Accuracy (Self-Check): {accuracy:.2%}")

    def save_output(self):
        # 1. Save Model (สำหรับใช้ในอนาคต)
        joblib.dump({
            'pipeline': self.pipeline,
            'label_encoder': self.label_encoder
        }, 'thai_emotion_model.pkl')
        
        # 2. Save JSON Final (สำหรับขึ้นเว็บ)
        # แปลง DataFrame กลับเป็น List of Dicts
        output_data = self.df.to_dict(orient='records')
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n💾 บันทึกไฟล์สำเร็จ!")
        print(f"   - โมเดล AI: thai_emotion_model.pkl")
        print(f"   - ข้อมูล JSON (Link+Emotion): {self.output_file}")

    def run(self):
        # โหลดไฟล์
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.df = pd.DataFrame(data)
            print(f"📂 โหลดข้อมูล {len(self.df)} เพลง จาก {self.input_file}")
            
            self.auto_label()      # 1. แปะป้าย
            self.build_and_train() # 2. เทรน AI
            self.save_output()     # 3. บันทึกผล
            
        except FileNotFoundError:
            print(f"❌ หาไฟล์ {self.input_file} ไม่เจอ! ตรวจสอบชื่อไฟล์ดีๆ")

# ==========================================
# ▶️ ส่วนสั่งงาน (Execution)
# ==========================================
if __name__ == "__main__":
    # ใส่ชื่อไฟล์ input ที่นายมี (ที่มี Link Spotify แล้ว)
    INPUT_FILE = 'thai_songs_spotify_only.json' 
    
    # ชื่อไฟล์ output ที่อยากได้
    OUTPUT_FILE = 'thai_songs_labeled_final.json'
    
    bot = ThaiMusicEmotionClassifier(INPUT_FILE, OUTPUT_FILE)
    bot.run()