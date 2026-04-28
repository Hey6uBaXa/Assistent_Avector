import subprocess
import numpy as np
import cv2
import time
from ultralytics import YOLO
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient
import threading
import torch


print("Доступен CUDA:", torch.cuda.is_available())
model = YOLO("yolo11n-seg.pt")
USE_YOLO = False
ChannelFactoryInitialize(0, "eth0")
client = VideoClient()
client.SetTimeout(3.0)
client.Init()

last = time.time()
frames = 0

ffmpeg_cmd = [
    "/home/unitree/ffmpeg-7.0.2-arm64-static/ffmpeg",  # путь к твоему ffmpeg
    "-f", "rawvideo",
    "-pix_fmt", "bgr24",
    "-s", "640x480",
    #"-g", "10",
    #"-crf", "28",
    "-r", "10",
    "-i", "-",
    "-vcodec", "libx264",
    "-preset", "ultrafast",
    "-tune", "zerolatency",
    "-f", "rtsp",
    "rtsp://127.0.0.1:8554/stream"  # отправляем в MediaMTX
]

pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

def log_ffmpeg_errors(pipe):
    for line in pipe.stderr:
        print("FFmpeg:", line.decode(errors="ignore").strip())

threading.Thread(target=log_ffmpeg_errors, args=(pipe,), daemon=True).start()

while True:
    code, data = client.GetImageSample()
    if code != 0 or not data:
        continue

    img = cv2.imdecode(np.frombuffer(bytes(data), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        continue

    if img.shape[:2] != (480, 640):
        img = cv2.resize(img, (640, 480))

    if USE_YOLO:
        results = model(img)
        annotated = results[0].plot()
    else:
        annotated = img
    try:
        pipe.stdin.write(memoryview(annotated))
    except BrokenPipeError:
        print("❌ ffmpeg завершился. Поток остановлен.")
        break

    frames += 1
    if time.time() - last >= 1.0:
        print(f"FPS: {frames}")
        frames = 0
        last = time.time()
