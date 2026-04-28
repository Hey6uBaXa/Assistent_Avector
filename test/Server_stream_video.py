from flask import Flask, Response
import cv2
import threading
import time

app = Flask(__name__)

cap = cv2.VideoCapture(2)  # подставь нужный индекс RealSense
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

latest_frame = None
lock = threading.Lock()

def camera_worker():
    global latest_frame
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue

        with lock:
            latest_frame = frame.copy()

def gen():
    while True:
        with lock:
            if latest_frame is None:
                continue
            ok, jpeg = cv2.imencode(".jpg", latest_frame)
            if not ok:
                continue
            data = jpeg.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
        )

@app.route("/video")
def video_feed():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    threading.Thread(target=camera_worker, daemon=True).start()
    app.run(host="192.168.100.163", port=5000, threaded=True)