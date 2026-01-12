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
from sklearn.metrics import classification_report

# ==========================================
# 🧠 CLASS: Thai Music Emotion Engine (Pure AI)
# ==========================================
class ThaiMusicEmotionClassifier:

    def __init__(self, input_file, output_file):
        self.input_file = input_file
        self.output_file = output_file
        self.pipeline = None
        self.label_encoder = None
        self.df = None

    def _clean_text(self, text):
        if not isinstance(text, str): return ""
        text = normalize(text) # PyThaiNLP Normalize
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'[0-9]+', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def _tokenizer(self, text):
        # ✂️ หัวใจสำคัญ: ใช้ PyThaiNLP ตัดคำเพื่อสร้าง Features ให้ TF-IDF
        text = self._clean_text(text)
        tokens = word_tokenize(text, engine='newmm', keep_whitespace=False)
        # กรอง Stopwords ออก เพื่อให้เหลือแต่คำที่มีความหมาย
        return [t for t in tokens if t not in thai_stopwords() and len(t) > 1]

    def build_and_train(self):
        print("\n🚀 กำลังเทรนโมเดล (TF-IDF + XGBoost)...")
        
        # 1. สร้าง Features ด้วย TF-IDF (Word + Char Level)
        # Word Level: จับคำศัพท์ที่มีความหมาย (ใช้ PyThaiNLP tokenizer)
        word_tfidf = TfidfVectorizer(tokenizer=self._tokenizer, ngram_range=(1, 2), max_features=2000)
        
        # Char Level: จับบริบทตัวอักษร (แก้ทางพวกพิมพ์ผิด หรือภาษาวิบัติ)
        char_tfidf = TfidfVectorizer(analyzer='char', ngram_range=(3, 5), max_features=3000)
        
        combined_features = FeatureUnion([
            ('word', word_tfidf),
            ('char', char_tfidf)
        ])
        
        # 2. Classifier Engine: XGBoost
        clf = xgb.XGBClassifier(
            n_estimators=300, 
            learning_rate=0.05, 
            max_depth=6,
            objective='multi:softprob', 
            eval_metric='mlogloss', 
            random_state=42
        )
        
        self.pipeline = Pipeline([('features', combined_features), ('clf', clf)])
        
        # Prepare Data
        # ⚠️ ต้องแน่ใจว่าใน JSON มีคอลัมน์ 'emotion' แล้ว
        X = self.df['lyrics'].fillna("")
        y_text = self.df['emotion'] 
        
        # แปลง Label ตัวหนังสือเป็นตัวเลข
        self.label_encoder = LabelEncoder()
        y = self.label_encoder.fit_transform(y_text)
        
        # Train
        print(f"   ... Feeding {len(X)} songs to AI")
        self.pipeline.fit(X, y)
        print("🎉 Training Complete!")
        
        # Self-Check Accuracy
        accuracy = self.pipeline.score(X, y)
        print(f"🏆 Model Accuracy: {accuracy:.2%}")

    def save_output(self):
        # Save Model
        joblib.dump({
            'pipeline': self.pipeline,
            'label_encoder': self.label_encoder
        }, 'thai_emotion_model.pkl')
        
        # Save JSON (Original Data)
        output_data = self.df.to_dict(orient='records')
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n💾 Saved model to 'thai_emotion_model.pkl'")

    def run(self):
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.df = pd.DataFrame(data)
            print(f"📂 Loaded {len(self.df)} songs")
            
            # Check Valid Data
            if 'lyrics' not in self.df.columns or 'emotion' not in self.df.columns:
                print("❌ Error: JSON ของคุณต้องมี key 'lyrics' และ 'emotion' เพื่อใช้เทรน")
                return

            self.build_and_train() # เทรนเลย ไม่ต้อง Label แล้ว
            self.save_output()
            
        except FileNotFoundError:
            print(f"❌ File not found: {self.input_file}")
        except Exception as e:
            print(f"❌ Error: {e}")

# ==========================================
# ▶️ EXECUTION
# ==========================================
if __name__ == "__main__":
    INPUT_FILE = 'thai_songs_spotify_only.json'
    OUTPUT_FILE = 'thai_songs_trained.json'
    
    bot = ThaiMusicEmotionClassifier(INPUT_FILE, OUTPUT_FILE)
    bot.run()