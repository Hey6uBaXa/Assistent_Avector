import time
import sys

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread
from unitree_sdk2py.comm.motion_switcher.motion_switcher_client import MotionSwitcherClient

import numpy as np

G1_NUM_MOTOR = 29

Kp = [
    60, 60, 60, 100, 40, 40,      # legs
    60, 60, 60, 100, 40, 40,      # legs
    60, 40, 40,                   # waist
    40, 40, 40, 40,  40, 40, 40,  # arms
    40, 40, 40, 40,  40, 40, 40   # arms
]

Kd = [
    1, 1, 1, 2, 1, 1,     # legs
    1, 1, 1, 2, 1, 1,     # legs
    1, 1, 1,              # waist
    1, 1, 1, 1, 1, 1, 1,  # arms
    1, 1, 1, 1, 1, 1, 1   # arms 
]

class G1JointIndex:
    # 🦵 Левая нога
    LeftHipPitch      = 0   # Сгибание/разгибание бедра (вперёд/назад)
    LeftHipRoll       = 1   # Боковой наклон бедра
    LeftHipYaw        = 2   # Вращение бедра вокруг вертикали
    LeftKnee          = 3   # Коленный сустав
    LeftAnklePitch    = 4   # Сгибание/разгибание голеностопа
    LeftAnkleB        = 4   # Альтернативное имя Pitch
    LeftAnkleRoll     = 5   # Боковой наклон голеностопа
    LeftAnkleA        = 5   # Альтернативное имя Roll

    # 🦵 Правая нога
    RightHipPitch     = 6   # Сгибание/разгибание бедра
    RightHipRoll      = 7   # Боковой наклон бедра
    RightHipYaw       = 8   # Вращение бедра
    RightKnee         = 9   # Коленный сустав
    RightAnklePitch   = 10  # Сгибание/разгибание голеностопа
    RightAnkleB       = 10  # Альтернативное имя Pitch
    RightAnkleRoll    = 11  # Боковой наклон голеностопа
    RightAnkleA       = 11  # Альтернативное имя Roll

    # 🧍 Таз и поясница (неактивны при заблокированной талии)
    WaistYaw          = 12  # Вращение талии
    WaistRoll         = 13  # Боковой наклон (неактивно для G1 23/29 DOF)
    WaistA            = 13  # Альтернативное имя Roll
    WaistPitch        = 14  # Сгибание/разгибание (неактивно)
    WaistB            = 14  # Альтернативное имя Pitch

    # 💪 Левая рука
    LeftShoulderPitch = 15  # Сгибание/разгибание плеча
    LeftShoulderRoll  = 16  # Боковой наклон плеча
    LeftShoulderYaw   = 17  # Вращение плеча
    LeftElbow         = 18  # Локтевой сустав
    LeftWristRoll     = 19  # Вращение кисти
    LeftWristPitch    = 20  # Сгибание/разгибание кисти (неактивно для G1 23 DOF)
    LeftWristYaw      = 21  # Вращение кисти вокруг вертикали (неактивно)

    # 💪 Правая рука
    RightShoulderPitch = 22 # Сгибание/разгибание плеча
    RightShoulderRoll  = 23 # Боковой наклон плеча
    RightShoulderYaw   = 24 # Вращение плеча
    RightElbow         = 25 # Локтевой сустав
    RightWristRoll     = 26 # Вращение кисти
    RightWristPitch    = 27 # Сгибание/разгибание кисти (неактивно)
    RightWristYaw      = 28 # Вращение кисти вокруг вертикали (неактивно)



class Mode:
    PR = 0  # Series Control for Pitch/Roll Joints
    AB = 1  # Parallel Control for A/B Joints

class Custom:
    def __init__(self):
        self.time_ = 0.0
        self.control_dt_ = 0.002  # [2ms]
        self.duration_ = 3.0    # [3 s]
        self.counter_ = 0
        self.mode_pr_ = Mode.PR
        self.mode_machine_ = 0
        self.low_cmd = unitree_hg_msg_dds__LowCmd_()  
        self.low_state = None 
        self.update_mode_machine_ = False
        self.crc = CRC()

    def Init(self):
        self.msc = MotionSwitcherClient()
        self.msc.SetTimeout(5.0)
        self.msc.Init()

        status, result = self.msc.CheckMode()
        while result['name']:
            self.msc.ReleaseMode()
            status, result = self.msc.CheckMode()
            time.sleep(1)

        # create publisher #
        self.lowcmd_publisher_ = ChannelPublisher("rt/lowcmd", LowCmd_)
        self.lowcmd_publisher_.Init()

        # create subscriber # 
        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init(self.LowStateHandler, 10)

    def Start(self):
        self.lowCmdWriteThreadPtr = RecurrentThread(
            interval=self.control_dt_, target=self.LowCmdWrite, name="control"
        )
        while self.update_mode_machine_ == False:
            time.sleep(1)

        if self.update_mode_machine_ == True:
            self.lowCmdWriteThreadPtr.Start()

    def LowStateHandler(self, msg: LowState_):
        self.low_state = msg

        if self.update_mode_machine_ == False:
            self.mode_machine_ = self.low_state.mode_machine
            self.update_mode_machine_ = True
        
        self.counter_ +=1
        if (self.counter_ % 500 == 0) :
            self.counter_ = 0
            print(self.low_state.imu_state.rpy)

    def LowCmdWrite(self):
        self.time_ += self.control_dt_

        if self.time_ < self.duration_ :
            # [Stage 1]: set robot to zero posture
            #for i in range(G1_NUM_MOTOR):

            i = 28  # Индекс мотора (например, RightElbow)
            # Вычисление коэффициента интерполяции от 0 до 1
            # Используется для плавного перехода между состояниями (например, отпускание сустава)
            ratio = np.clip(self.time_ / self.duration_, 0.0, 1.0)
            # Если time_ < 0 → ratio = 0, если time_ > duration_ → ratio = 1
            # Установка режима управления по положению и скорости
            self.low_cmd.mode_pr = Mode.PR  # Режим PR: позиция + скорость + PID
            # Установка режима машины (например, стояние, ходьба, переход)
            self.low_cmd.mode_machine = self.mode_machine_  # Текущий режим машины (внешняя логика)
            # Активация управления мотором i
            self.low_cmd.motor_cmd[i].mode = 1  # Режим мотора: 1 — включить, 0 — выключить
            # Установка момента (torque) в 0 — управление по положению, без усилия
            self.low_cmd.motor_cmd[i].tau = 0.  # Мгновенное значение момента (не используется)
            # Целевое положение сустава: интерполяция между текущим положением и нулевым
            # Локоть 25: 1.7 - согнут назад, -1 - согнут вперёд
            # Пличо 22: 1.7 - поднят назад, -3 - поднят вверх вперёд 
            # Плечо 23: 0.3 - Прижато к телу, -2.3 поднят вверх вбок
            # Врашение плеча 24: 2.3 вращение во внутрь, -1.5 вращение наружу
            # Вращение кисти 26: 1.5 вращение наружу, -1.5 вращение во внутрь 
            # Подъём кисти 27: 1 назад, -1 вперёд
            # Подъём кисти 28: 1 во внутрь, -1 наружу
            target_angle = -1
            self.low_cmd.motor_cmd[i].q = (1.0 - ratio) * self.low_state.motor_state[i].q + ratio * target_angle
            # Это позволяет плавно "отпустить" суставы, например, при выключении
            # Целевая скорость — 0 (статическое удержание)
            self.low_cmd.motor_cmd[i].dq = 0.  # Целевая скорость вращения
            # Пропорциональный коэффициент управления (жесткость)
            self.low_cmd.motor_cmd[i].kp = Kp[i]  # Коэффициент P — отвечает за реакцию на отклонение
            # Дифференциальный коэффициент управления (демпфирование)
            self.low_cmd.motor_cmd[i].kd = Kd[i]  # Коэффициент D — отвечает за реакцию на скорость


        # elif self.time_ < self.duration_ * 2 :
        #     # [Stage 2]: swing ankle using PR mode
        #     max_P = np.pi * 30.0 / 180.0
        #     max_R = np.pi * 10.0 / 180.0
        #     t = self.time_ - self.duration_
        #     L_P_des = max_P * np.sin(2.0 * np.pi * t)
        #     L_R_des = max_R * np.sin(2.0 * np.pi * t)
        #     R_P_des = max_P * np.sin(2.0 * np.pi * t)
        #     R_R_des = -max_R * np.sin(2.0 * np.pi * t)

        #     self.low_cmd.mode_pr = Mode.PR
        #     self.low_cmd.mode_machine = self.mode_machine_
        #     self.low_cmd.motor_cmd[G1JointIndex.LeftAnklePitch].q = L_P_des
        #     self.low_cmd.motor_cmd[G1JointIndex.LeftAnkleRoll].q = L_R_des
        #     self.low_cmd.motor_cmd[G1JointIndex.RightAnklePitch].q = R_P_des
        #     self.low_cmd.motor_cmd[G1JointIndex.RightAnkleRoll].q = R_R_des

        # else :
        #     # [Stage 3]: swing ankle using AB mode
        #     max_A = np.pi * 30.0 / 180.0
        #     max_B = np.pi * 10.0 / 180.0
        #     t = self.time_ - self.duration_ * 2
        #     L_A_des = max_A * np.sin(2.0 * np.pi * t)
        #     L_B_des = max_B * np.sin(2.0 * np.pi * t + np.pi)
        #     R_A_des = -max_A * np.sin(2.0 * np.pi * t)
        #     R_B_des = -max_B * np.sin(2.0 * np.pi * t + np.pi)

        #     self.low_cmd.mode_pr = Mode.AB
        #     self.low_cmd.mode_machine = self.mode_machine_
        #     self.low_cmd.motor_cmd[G1JointIndex.LeftAnkleA].q = L_A_des
        #     self.low_cmd.motor_cmd[G1JointIndex.LeftAnkleB].q = L_B_des
        #     self.low_cmd.motor_cmd[G1JointIndex.RightAnkleA].q = R_A_des
        #     self.low_cmd.motor_cmd[G1JointIndex.RightAnkleB].q = R_B_des
            
        #     max_WristYaw = np.pi * 30.0 / 180.0
        #     L_WristYaw_des = max_WristYaw * np.sin(2.0 * np.pi * t)
        #     R_WristYaw_des = max_WristYaw * np.sin(2.0 * np.pi * t)
        #     self.low_cmd.motor_cmd[G1JointIndex.LeftWristRoll].q = L_WristYaw_des
        #     self.low_cmd.motor_cmd[G1JointIndex.RightWristRoll].q = R_WristYaw_des
    

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.lowcmd_publisher_.Write(self.low_cmd)

if __name__ == '__main__':

    # print("WARNING: Please ensure there are no obstacles around the robot while running this example.")
    # input("Press Enter to continue...")

    ChannelFactoryInitialize(0, "eth0")

    custom = Custom()
    custom.Init()
    custom.Start()

    while True:        
        time.sleep(1)