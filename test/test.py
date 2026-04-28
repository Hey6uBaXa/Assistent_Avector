import numpy as np
from ultralytics import YOLO
import cv2


model = YOLO("yolo11n-pose.pt")
results = model(source="2", show=False, stream=True)  # Камера или видео

for r in results:
    keypoints = r.keypoints.xy  # [n_persons, n_keypoints, 2]

    if len(keypoints) == 0:
        continue

    # Возьмём первого человека
    kp = keypoints[0]  # [n_keypoints, 2]

    # Пример: вычисление угла в локте (левый локоть)
    shoulder = kp[5]  # LeftShoulder
    elbow = kp[7]     # LeftElbow
    wrist = kp[9]     # LeftWrist

    def angle_between(p1, p2, p3):
        v1 = p1 - p2
        v2 = p3 - p2
        angle = np.arccos(
            np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)), -1.0, 1.0)
        )
        return angle  # в радианах

    left_elbow_angle = angle_between(shoulder, elbow, wrist)

    # Преобразуем в команду для мотора
    #i = 18  # индекс сустава LeftElbow
    #ratio = np.clip(self.time_ / self.duration_, 0.0, 1.0)
    #self.low_cmd.motor_cmd[i].q = (1.0 - ratio) * left_elbow_angle
    print(left_elbow_angle)



