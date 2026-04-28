import time
import numpy as np
from ultralytics import YOLO
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_, unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread
from unitree_sdk2py.comm.motion_switcher.motion_switcher_client import MotionSwitcherClient

G1_NUM_MOTOR = 29

Kp = [60, 60, 60, 100, 40, 40, 60, 60, 60, 100, 40, 40, 60, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40]
Kd = [1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

class G1JointIndex:
    RightShoulderPitch = 22
    RightShoulderRoll  = 23
    RightShoulderYaw   = 24
    RightElbow         = 25
    RightWristRoll     = 26
    RightWristPitch    = 27
    RightWristYaw      = 28
    # Left joints закомментированы для теста

class Mode:
    PR = 0
    AB = 1

def angle_between(p1, p2, p3):
    v1 = p1 - p2
    v2 = p3 - p2
    angle = np.arccos(
        np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)), -1.0, 1.0)
    )
    return angle

def signed_angle(p1, p2):
    v = p2 - p1
    angle = np.arctan2(v[1], v[0])
    return angle

def remap(value, src_min, src_max, dst_min, dst_max):
    value = np.clip(value, src_min, src_max)
    return dst_min + (value - src_min) * (dst_max - dst_min) / (src_max - src_min)


class Custom:
    def __init__(self):
        self.time_ = 0.0
        self.control_dt_ = 0.02
        self.duration_ = 3.0
        self.counter_ = 0
        self.mode_machine_ = 0
        self.low_cmd = unitree_hg_msg_dds__LowCmd_()
        self.low_state = None
        self.update_mode_machine_ = False
        self.crc = CRC()
        self.model = YOLO("yolo11n-pose.pt")
        self.results = self.model(source="2", show=False, stream=True )

    def Init(self):
        self.msc = MotionSwitcherClient()
        self.msc.SetTimeout(5.0)
        self.msc.Init()
        status, result = self.msc.CheckMode()
        while result['name']:
            self.msc.ReleaseMode()
            status, result = self.msc.CheckMode()
            time.sleep(1)
        self.lowcmd_publisher_ = ChannelPublisher("rt/lowcmd", LowCmd_)
        self.lowcmd_publisher_.Init()
        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init(self.LowStateHandler, 10)

    def Start(self):
        self.lowCmdWriteThreadPtr = RecurrentThread(
            interval=self.control_dt_, target=self.LowCmdWrite, name="control"
        )
        while not self.update_mode_machine_:
            time.sleep(1)
        self.lowCmdWriteThreadPtr.Start()

    def LowStateHandler(self, msg: LowState_):
        self.low_state = msg
        if not self.update_mode_machine_:
            self.mode_machine_ = self.low_state.mode_machine
            self.update_mode_machine_ = True
    
    def LowCmdWrite(self):
        self.time_ += self.control_dt_
        ratio = np.clip(self.time_ / self.duration_, 0.0, 1.0)

        self.low_cmd.mode_pr = Mode.PR
        self.low_cmd.mode_machine = self.mode_machine_

        for r in self.results:
            keypoints = r.keypoints.xy
            if len(keypoints) == 0:
                continue

            kp = keypoints[0]

            # Правое плечо и локоть
            shoulder = kp[6]
            elbow = kp[8]
            wrist = kp[10]
            neck = kp[0]
            chest = kp[12]

            # Визуальные углы
            shoulder_pitch_vis = angle_between(neck, shoulder, elbow)       # вперёд/назад
            shoulder_roll_vis  = angle_between(chest, shoulder, elbow)      # вверх/вбок
            shoulder_yaw_vis   = signed_angle(shoulder, elbow)              # вращение
            elbow_bend_vis     = angle_between(shoulder, elbow, wrist)      # сгибание

            # Преобразование в моторные значения
            shoulder_pitch_motor = remap(np.degrees(shoulder_pitch_vis), 0, 90, -3.0, 1.7)
            shoulder_roll_motor  = remap(np.degrees(shoulder_roll_vis), 0, 90, 0.3, -2.3)
            shoulder_yaw_motor   = remap(np.degrees(shoulder_yaw_vis), -90, 90, -1.5, 2.3)
            elbow_motor          = remap(np.degrees(elbow_bend_vis), 0, 150, -1.0, 1.7)

            # Плавная интерполяция
            for i, target_angle in zip(
                [G1JointIndex.RightShoulderPitch, G1JointIndex.RightShoulderRoll,
                G1JointIndex.RightShoulderYaw, G1JointIndex.RightElbow],
                [shoulder_pitch_motor, shoulder_roll_motor, shoulder_yaw_motor, elbow_motor]
            ):
                current_angle = self.low_state.motor_state[i].q
                interpolated_angle = (1.0 - ratio) * current_angle + ratio * target_angle

                self.low_cmd.motor_cmd[i].mode = 1
                self.low_cmd.motor_cmd[i].tau = 0.
                self.low_cmd.motor_cmd[i].q = interpolated_angle
                self.low_cmd.motor_cmd[i].dq = 0.
                self.low_cmd.motor_cmd[i].kp = Kp[i]
                self.low_cmd.motor_cmd[i].kd = Kd[i]

            break  # Только первый человек

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.lowcmd_publisher_.Write(self.low_cmd)




if __name__ == '__main__':
    ChannelFactoryInitialize(0, "eth0")
    custom = Custom()
    custom.Init()
    custom.Start()
    while True:
        time.sleep(1)
