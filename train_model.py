import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import matplotlib.pyplot as plt
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Dense, Flatten, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau

# 1. กำหนดค่า Parameters
IMG_SIZE = 48
BATCH_SIZE = 64
EPOCHS = 50
NUM_CLASSES = 7  # angry, disgust, fear, happy, neutral, sad, surprise

# 2. สร้าง Image Generator (ทำ Data Augmentation)
train_datagen = ImageDataGenerator(
    rescale=1./255,           # ปรับค่าสีจาก 0-255 เป็น 0-1
    rotation_range=10,        # หมุนภาพเล็กน้อย
    width_shift_range=0.1,    # เลื่อนซ้ายขวา
    height_shift_range=0.1,   # เลื่อนขึ้นลง
    zoom_range=0.1,           # ซูมเข้าออก
    horizontal_flip=True,     # กลับด้านซ้ายขวา
    fill_mode='nearest'
)

val_datagen = ImageDataGenerator(rescale=1./255) # ข้อมูล Test ไม่ต้องบิดภาพ แค่ปรับ scale

# 3. โหลดข้อมูลจาก Folder
train_generator = train_datagen.flow_from_directory(
    'data/train',             # โฟลเดอร์เก็บรูป Train
    target_size=(IMG_SIZE, IMG_SIZE),
    color_mode='grayscale',   # FER2013 เป็นขาวดำ
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=True
)

validation_generator = val_datagen.flow_from_directory(
    'data/test',              # โฟลเดอร์เก็บรูป Test
    target_size=(IMG_SIZE, IMG_SIZE),
    color_mode='grayscale',
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=False
)

# 4. สร้างโมเดล CNN

def build_model():
    model = Sequential()

    # Block 1
    model.add(Conv2D(32, kernel_size=(3, 3), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, 1)))
    model.add(BatchNormalization())
    model.add(Conv2D(64, kernel_size=(3, 3), activation='relu'))
    model.add(BatchNormalization())
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    # Block 2
    model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
    model.add(BatchNormalization())
    model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
    model.add(BatchNormalization())
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    # Block 3
    model.add(Conv2D(256, kernel_size=(3, 3), activation='relu'))
    model.add(BatchNormalization())
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    # Flatten & Dense Layers
    model.add(Flatten())
    model.add(Dense(256, activation='relu'))
    model.add(BatchNormalization())
    model.add(Dropout(0.5))
    
    # Output Layer (7 อารมณ์)
    model.add(Dense(NUM_CLASSES, activation='softmax'))

    # Compile Model
    opt = Adam(learning_rate=0.0005) # ค่า Learning rate ต่ำๆ จะช่วยให้เรียนรู้ละเอียดขึ้น
    model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['accuracy'])
    
    return model

model = build_model()
model.summary() # ดูโครงสร้างโมเดล


# 5. ฝึกโมเดล
# ตั้งค่า Callbacks
checkpoint = ModelCheckpoint(
    'emotion_model_best.keras', # ชื่อไฟล์ที่จะเซฟ
    monitor='val_accuracy',
    save_best_only=True,
    mode='max',
    verbose=1
)

early_stopping = EarlyStopping(
    monitor='val_loss',
    patience=10,
    verbose=1,
    restore_best_weights=True
)

reduce_lr = ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.2,
    patience=5,
    verbose=1,
    min_lr=0.00001
)

# เริ่มเทรน!
history = model.fit(
    train_generator,
    steps_per_epoch=train_generator.n // train_generator.batch_size,
    epochs=EPOCHS,
    validation_data=validation_generator,
    validation_steps=validation_generator.n // validation_generator.batch_size,
    callbacks=[checkpoint, early_stopping, reduce_lr]
)

# 6. ประเมินผลโมเดล
val_loss, val_accuracy = model.evaluate(validation_generator)
# พล็อตกราฟ Accuracy และ Loss
plt.figure(figsize=(14,5))
plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'], label='Train')
plt.plot(history.history['val_accuracy'], label='Validation')
plt.title('Model Accuracy')
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(history.history['loss'], label='Train')
plt.plot(history.history['val_loss'], label='Validation')
plt.title('Model Loss')
plt.legend()
plt.show()