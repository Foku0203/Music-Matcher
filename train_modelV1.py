import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.layers import Input, Conv2D, SeparableConv2D, MaxPooling2D
from tensorflow.keras.layers import GlobalAveragePooling2D, BatchNormalization, Activation, Add
from tensorflow.keras.models import Model
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from sklearn.utils import class_weight
import numpy as np
import matplotlib.pyplot as plt
import os

# ==========================================
# 1. ⚙️ CONFIGURATION (ตั้งค่า)
# ==========================================
IMG_SIZE = 48    # ขนาดภาพมาตรฐาน FER2013
BATCH_SIZE = 64  # เพิ่ม Batch size ได้เพราะโมเดลเบา
EPOCHS = 100     # เทรนยาวๆ ได้เลย โมเดลนี้ยิ่งเทรนนานยิ่งดี
DATA_DIR = 'FER2013DATA' # โฟลเดอร์ข้อมูล

# ตรวจสอบ GPU
print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))

# ==========================================
# 2. 📂 DATA GENERATORS (เตรียมข้อมูล)
# ==========================================
# Mini-Xception ชอบภาพ Grayscale (channel=1)
train_datagen = ImageDataGenerator(
    featurewise_center=False,
    featurewise_std_normalization=False,
    rotation_range=10,
    width_shift_range=0.1,
    height_shift_range=0.1,
    zoom_range=.1,
    horizontal_flip=True
)

val_datagen = ImageDataGenerator() # ไม่ต้อง preprocess อะไรมากสำหรับ Validation

print("\n🚀 กำลังโหลดรูปภาพ...")
train_generator = train_datagen.flow_from_directory(
    os.path.join(DATA_DIR, 'train'),
    target_size=(IMG_SIZE, IMG_SIZE),
    color_mode='grayscale',  # ⚠️ เปลี่ยนเป็นขาวดำ
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=True
)

validation_generator = val_datagen.flow_from_directory(
    os.path.join(DATA_DIR, 'test'),
    target_size=(IMG_SIZE, IMG_SIZE),
    color_mode='grayscale',  # ⚠️ เปลี่ยนเป็นขาวดำ
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=False
)

# คำนวณ Class Weights
print("\n⚖️ กำลังคำนวณ Class Weights...")
class_weights_val = class_weight.compute_class_weight(
    class_weight='balanced',
    classes=np.unique(train_generator.classes),
    y=train_generator.classes
)
train_class_weights = dict(enumerate(class_weights_val))
print(f"Weights: {train_class_weights}")

# ==========================================
# 3. 🧠 MODEL ARCHITECTURE (Mini-Xception Fixed)
# ==========================================
def build_mini_xception(input_shape=(48, 48, 1), num_classes=7, l2_reg=0.01):
    regularization = l2(l2_reg)

    # Input Image
    img_input = Input(input_shape)
    
    # Block 1: Conv ธรรมดา
    x = Conv2D(8, (3, 3), strides=(1, 1), kernel_regularizer=regularization, use_bias=False)(img_input)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)
    
    x = Conv2D(8, (3, 3), strides=(1, 1), kernel_regularizer=regularization, use_bias=False)(x)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)
    
    # Blocks 2-5: Residual Blocks (ใช้ Depthwise/Pointwise Regularizer แทน Kernel)
    for filters in [16, 32, 64, 128]:
        residual = Conv2D(filters, (1, 1), strides=(2, 2), padding='same', use_bias=False)(x)
        residual = BatchNormalization()(residual)
        
        # ⚠️ FIX: เปลี่ยน kernel_regularizer เป็น pointwise_regularizer
        x = SeparableConv2D(filters, (3, 3), padding='same', 
                            pointwise_regularizer=regularization, 
                            depthwise_regularizer=regularization,
                            use_bias=False)(x)
        x = BatchNormalization()(x)
        x = Activation('relu')(x)
        
        x = SeparableConv2D(filters, (3, 3), padding='same', 
                            pointwise_regularizer=regularization, 
                            depthwise_regularizer=regularization,
                            use_bias=False)(x)
        x = BatchNormalization()(x)
        x = MaxPooling2D((3, 3), strides=(2, 2), padding='same')(x)
        
        x = Add()([x, residual]) # Skip Connection
        
    # Output Block
    x = Conv2D(num_classes, (3, 3), padding='same', kernel_regularizer=regularization, use_bias=False)(x)
    x = GlobalAveragePooling2D()(x)
    output = Activation('softmax', name='predictions')(x)

    model = Model(img_input, output)
    return model

model = build_mini_xception()
model.summary()

# ==========================================
# 4. 🏋️ TRAINING
# ==========================================
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Callbacks
checkpoint = ModelCheckpoint(
    'mini_xception_best.keras', 
    monitor='val_accuracy',
    save_best_only=True,
    mode='max',
    verbose=1
)

early_stopping = EarlyStopping(
    monitor='val_loss',
    patience=10, # รอหน่อย โมเดลนี้บางทีลงช้าแต่ลงเรื่อยๆ
    restore_best_weights=True,
    verbose=1
)

reduce_lr = ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.5,
    patience=5,
    min_lr=1e-7,
    verbose=1
)

print("\n🚀 เริ่มเทรน Mini-Xception...")
history = model.fit(
    train_generator,
    steps_per_epoch=len(train_generator),
    epochs=EPOCHS, 
    validation_data=validation_generator,
    validation_steps=len(validation_generator),
    callbacks=[checkpoint, early_stopping, reduce_lr],
    class_weight=train_class_weights 
)

print("\n✅ เทรนเสร็จสมบูรณ์! บันทึกโมเดลเรียบร้อย")

# ==========================================
# 5. 📊 PLOT RESULTS
# ==========================================
acc = history.history['accuracy']
val_acc = history.history['val_accuracy']
loss = history.history['loss']
val_loss = history.history['val_loss']

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(acc, label='Train Accuracy')
plt.plot(val_acc, label='Val Accuracy')
plt.title('Accuracy')
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(loss, label='Train Loss')
plt.plot(val_loss, label='Val Loss')
plt.title('Loss')
plt.legend()

plt.show()