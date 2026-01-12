import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.applications.efficientnet import preprocess_input

# 1. โหลดโมเดล
print("Loading model...")
model = load_model('efficientnet_fer_best.keras')
EMOTIONS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# 2. ฟังก์ชันเตรียมรูป (ต้องทำให้เหมือนตอนเทรนเป๊ะๆ)
def prepare_image(frame):
    # แปลงเป็นขาวดำก่อน (เพื่อตัดเรื่องสีเพี้ยน)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Resize เป็น 48x48
    resized = cv2.resize(gray, (48, 48))
    # แปลงกลับเป็น RGB (Fake RGB) เพื่อหลอกโมเดล
    img_rgb = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)
    # ขยายมิติและ Preprocess
    img_array = np.expand_dims(img_rgb, axis=0)
    return preprocess_input(img_array)

# 3. เปิดกล้อง Webcam
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret: break

    # จับหน้าคน (ใช้ Haar Cascade แบบพื้นฐาน)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray_frame, 1.3, 5)

    for (x, y, w, h) in faces:
        # ตัดส่วนใบหน้า
        roi_color = frame[y:y+h, x:x+w]
        
        # ส่งเข้าโมเดล
        try:
            processed_img = prepare_image(roi_color)
            prediction = model.predict(processed_img, verbose=0)
            idx = np.argmax(prediction)
            label = EMOTIONS[idx]
            confidence = np.max(prediction) * 100

            # วาดกรอบและชื่อ
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} ({confidence:.1f}%)", (x, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        except Exception as e:
            pass

    cv2.imshow('Emotion Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()