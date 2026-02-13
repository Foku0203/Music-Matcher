import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from sklearn.utils import class_weight
import numpy as np
import matplotlib.pyplot as plt
import os

# ==========================================
# 1. ⚙️ CONFIGURATION (ตั้งค่า)
# ==========================================
IMG_SIZE = 224   # ขนาดภาพสำหรับ EfficientNet
BATCH_SIZE = 32  # ถ้าแรมการ์ดจอเต็ม ให้ลดเหลือ 16
EPOCHS = 40      # จำนวนรอบสูงสุด (มี Early Stopping ช่วยหยุดถ้าผลไม่ดีขึ้น)
DATA_DIR = 'FER2013DATA' # โฟลเดอร์ข้อมูล

# ตรวจสอบ GPU
print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))

# ==========================================
# 2. 📂 DATA GENERATORS (เตรียมข้อมูล)
# ==========================================
train_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input,
    rotation_range=20,
    width_shift_range=0.1,
    height_shift_range=0.1,
    shear_range=0.1,
    zoom_range=0.1,
    horizontal_flip=True,
    fill_mode='nearest'
)

val_datagen = ImageDataGenerator(preprocessing_function=preprocess_input)

print("\n🚀 กำลังโหลดรูปภาพ...")
train_generator = train_datagen.flow_from_directory(
    os.path.join(DATA_DIR, 'train'),
    target_size=(IMG_SIZE, IMG_SIZE),
    color_mode='rgb',
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=True
)

validation_generator = val_datagen.flow_from_directory(
    os.path.join(DATA_DIR, 'test'),
    target_size=(IMG_SIZE, IMG_SIZE),
    color_mode='rgb',
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=False
)

# คำนวณ Class Weights เพื่อแก้ปัญหาข้อมูลไม่สมดุล
print("\n⚖️ กำลังคำนวณ Class Weights...")
class_weights_val = class_weight.compute_class_weight(
    class_weight='balanced',
    classes=np.unique(train_generator.classes),
    y=train_generator.classes
)
train_class_weights = dict(enumerate(class_weights_val))
print(f"Weights: {train_class_weights}")

# ==========================================
# 3. 🧠 MODEL ARCHITECTURE (สร้างโมเดล)
# ==========================================
def build_model():
    base_model = EfficientNetB0(
        include_top=False,
        weights='imagenet',
        input_shape=(IMG_SIZE, IMG_SIZE, 3) 
    )
    
    # Freeze Base Model ไว้ก่อน
    base_model.trainable = False 

    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = BatchNormalization()(x)  # ช่วยให้เทรนเสถียร
    x = Dense(256, activation='relu')(x)
    x = Dropout(0.5)(x)          # กัน Overfitting
    outputs = Dense(7, activation='softmax')(x) 

    model = Model(inputs=base_model.input, outputs=outputs)
    return model, base_model

model, base_model = build_model()

# ==========================================
# 4. 🏋️ TRAINING PHASE 1: WARM-UP
# ==========================================
print("\n🔥 Phase 1: Training Top Layers (Warm-up)...")
# เทรนเฉพาะส่วนหัวด้วย Learning Rate ปกติ
model.compile(optimizer=Adam(learning_rate=0.001), 
              loss='categorical_crossentropy', 
              metrics=['accuracy'])

# ⚠️ สังเกต: ไม่ใส่ steps_per_epoch เพื่อแก้ปัญหา Input ran out of data
history_warmup = model.fit(
    train_generator,
    epochs=5,  
    validation_data=validation_generator,
    class_weight=train_class_weights
)

# ==========================================
# 5. 🏋️ TRAINING PHASE 2: FINE-TUNING
# ==========================================
print("\n🔓 Phase 2: Fine-tuning Whole Model (Unfreezing)...")
base_model.trainable = True # ปลดล็อคทุกชั้น

# ใช้ Learning Rate ต่ำมาก เพื่อจูนละเอียด
model.compile(optimizer=Adam(learning_rate=1e-5), 
              loss='categorical_crossentropy', 
              metrics=['accuracy'])

# Callbacks
checkpoint = ModelCheckpoint(
    'efficientnet_fer_best.keras', 
    monitor='val_accuracy',
    save_best_only=True,
    mode='max',
    verbose=1
)

early_stopping = EarlyStopping(
    monitor='val_loss',
    patience=8,
    restore_best_weights=True,
    verbose=1
)

reduce_lr = ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.2,
    patience=3,
    min_lr=1e-7,
    verbose=1
)

print("🚀 เริ่ม Fine-tuning ยาวๆ...")
history = model.fit(
    train_generator,
    epochs=EPOCHS, 
    validation_data=validation_generator,
    callbacks=[checkpoint, early_stopping, reduce_lr],
    class_weight=train_class_weights 
)

print("\n✅ เทรนเสร็จสมบูรณ์! บันทึกโมเดลเรียบร้อย")

# ==========================================
# 6. 📊 PLOT RESULTS (กราฟผลลัพธ์)
# ==========================================
# รวมประวัติการเทรนทั้ง 2 ช่วง
acc = history_warmup.history['accuracy'] + history.history['accuracy']
val_acc = history_warmup.history['val_accuracy'] + history.history['val_accuracy']
loss = history_warmup.history['loss'] + history.history['loss']
val_loss = history_warmup.history['val_loss'] + history.history['val_loss']

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(acc, label='Train Accuracy')
plt.plot(val_acc, label='Val Accuracy')
plt.axvline(x=5, color='green', linestyle='--', label='Start Fine-tuning')
plt.title('Accuracy')
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(loss, label='Train Loss')
plt.plot(val_loss, label='Val Loss')
plt.axvline(x=5, color='green', linestyle='--', label='Start Fine-tuning')
plt.title('Loss')
plt.legend()

plt.show()