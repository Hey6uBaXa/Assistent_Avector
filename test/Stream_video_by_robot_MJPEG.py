from flask import Flask, Response
import cv2
import numpy as np
import threading
import time
from ultralytics import YOLO
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient

# Загружаем легкую модель YOLO
model = YOLO("yolo11n-seg.pt")  # или yolov8n-seg.pt

# Инициализируем видеоклиент Unitree
ChannelFactoryInitialize(0, "eth0")
client = VideoClient()
client.SetTimeout(3.0)
client.Init()

# Буфер для последнего кадра
latest_frame = None
lock = threading.Lock()

# Фоновый поток для YOLO-инференса
def yolo_worker():
    global latest_frame
    while True:
        code, data = client.GetImageSample()
        if code != 0 or not data:
            continue

        img = cv2.imdecode(np.frombuffer(bytes(data), np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue

        # Уменьшаем разрешение для ускорения
        img = cv2.resize(img, (320, 240))

        results = model(img)
        annotated = results[0].plot()

        with lock:
            latest_frame = annotated

# MJPEG-генератор
def gen():
    while True:
        with lock:
            if latest_frame is None:
                continue
            _, jpeg = cv2.imencode('.jpg', latest_frame)
            frame = jpeg.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        #time.sleep(1)  # ~30 fps

# Flask-приложение
app = Flask(__name__)

@app.route('/video')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Запуск
if __name__ == '__main__':
    threading.Thread(target=yolo_worker, daemon=True).start()
    app.run(host='192.168.100.163', port=5000)
