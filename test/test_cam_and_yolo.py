import time
import sys
import numpy as np
import cv2
from ultralytics import YOLO
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient

if __name__ == "__main__":
    # Load a model
    model = YOLO("yolo11n-seg.pt")

    ChannelFactoryInitialize(0, "eth0")

    client = VideoClient()
    client.SetTimeout(3.0)
    client.Init()

    print("##################GetImageSample###################")
    code, data = client.GetImageSample()
    print(code)
    print(data)
    if code != 0:
        print("get image sample error. code:", code)
    else:
        # Convert raw bytes to NumPy array
        np_data = np.frombuffer(bytes(data), dtype=np.uint8)
        img = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

        # Run prediction directly on the image array
        results = model(img)

        # Save annotated result to file
        results[0].save(filename="images/image.jpg")

    time.sleep(1)