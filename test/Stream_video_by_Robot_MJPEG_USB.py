from flask import Flask, Response
import cv2
import numpy as np
import threading
from ultralytics import YOLO

model = YOLO("yolo11n-seg.pt")

cap = cv2.VideoCapture(2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

latest_frame = None
lock = threading.Lock()

def yolo_worker():
    global latest_frame
    while True:
        ret, img = cap.read()
        if not ret or img is None:
            continue

        img = cv2.resize(img, (320, 240))
        results = model(img)
        annotated = results[0].plot()

        with lock:
            latest_frame = annotated

def gen():
    while True:
        with lock:
            if latest_frame is None:
                continue
            _, jpeg = cv2.imencode('.jpg', latest_frame)
            frame = jpeg.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

app = Flask(__name__)

@app.route('/video')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    threading.Thread(target=yolo_worker, daemon=True).start()
    app.run(host='192.168.100.163', port=5000)