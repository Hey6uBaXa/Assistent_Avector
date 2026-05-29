import time
import struct
from robot_interface import RobotInterface
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from libs.config import TEXT
import threading
# Uncomment the following two lines when using Go2、Go2-W、B2、B2-W、H1 robot
# from unitree_sdk2py.idl.default import unitree_go_msg_dds__LowState_
# from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_

# Uncomment the following two lines when using G1、H1-2 robot
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_



class unitreeRemoteController:
    def __init__(self):
        # key
        self.Lx = 0           
        self.Rx = 0            
        self.Ry = 0            
        self.Ly = 0

        # button
        self.L1 = 0
        self.L2 = 0
        self.R1 = 0
        self.R2 = 0
        self.A = 0
        self.B = 0
        self.X = 0
        self.Y = 0
        self.Up = 0
        self.Down = 0
        self.Left = 0
        self.Right = 0
        self.Select = 0
        self.F1 = 0
        self.F3 = 0
        self.Start = 0

        # variable
        self.t1 = None
        self.t2 = None
        self.t3 = None
        self.t4 = None
        self.t5 = None
        self.t6 = None
        self.t7 = None
        self.t8 = None

        self.flag1 = True
        self.flag2 = True
        self.flag3 = True
        self.flag4 = True
        self.flag5 = True
        self.flag6 = True
        self.flag7 = True
        self.flag8 = True

        self.index = 1
        self.index_fu = 6
        
    def parse_botton(self,data1,data2):
        self.R1 = (data1 >> 0) & 1
        self.L1 = (data1 >> 1) & 1
        self.Start = (data1 >> 2) & 1
        self.Select = (data1 >> 3) & 1
        self.R2 = (data1 >> 4) & 1
        self.L2 = (data1 >> 5) & 1
        self.F1 = (data1 >> 6) & 1
        self.F3 = (data1 >> 7) & 1
        self.A = (data2 >> 0) & 1
        self.B = (data2 >> 1) & 1
        self.X = (data2 >> 2) & 1
        self.Y = (data2 >> 3) & 1
        self.Up = (data2 >> 4) & 1
        self.Right = (data2 >> 5) & 1
        self.Down = (data2 >> 6) & 1
        self.Left = (data2 >> 7) & 1

    def parse_key(self,data):
        lx_offset = 4
        self.Lx = struct.unpack('<f', data[lx_offset:lx_offset + 4])[0]
        rx_offset = 8
        self.Rx = struct.unpack('<f', data[rx_offset:rx_offset + 4])[0]
        ry_offset = 12
        self.Ry = struct.unpack('<f', data[ry_offset:ry_offset + 4])[0]
        L2_offset = 16
        L2 = struct.unpack('<f', data[L2_offset:L2_offset + 4])[0] # Placeholder，unused
        ly_offset = 20
        self.Ly = struct.unpack('<f', data[ly_offset:ly_offset + 4])[0]


    def parse(self,remoteData):
        self.parse_key(remoteData)
        self.parse_botton(remoteData[2],remoteData[3])

        # print("debug unitreeRemoteController: ")
        # print("Lx:", self.Lx)
        # print("Rx:", self.Rx)
        # print("Ry:", self.Ry)
        # print("Ly:", self.Ly)

        # print("L1:", se
        # print("L2:", self.L2)
        # print("R1:", self.R1)
        # print("R2:", self.R2)
        # print("A:", self.A)
        # print("B:", self.B)
        # print("X:", self.X)
        # print("Y:", self.Y)
        # print("Up:", self.Up)
        # print("Down:", self.Down)
        # print("Left:", self.Left)
        # print("Right:", self.Right)
        # print("Select:", self.Select)
        # print("F1:", self.F1)
        # print("F3:", self.F3)
        # print("Start:", self.Start)
        # print("\n")

        if self.F1:
            if self.t1 is None or not self.t1.is_alive():
                if self.flag1:
                    self.t1 = threading.Thread(target=RobotInterface.handshake)
                    self.t1.start()
                    self.flag1 = False
            else:
                self.flag1 = True

        if self.F3:
            if self.t2 is None or not self.t2.is_alive():
                if self.flag2:
                    self.t2 = threading.Thread(target=RobotInterface.cristmas_tree_event_voice, args=(self.index,))
                    self.t3 = threading.Thread(target=RobotInterface.cristmas_tree_event_action, args=(self.index,))
                    self.t2.start()
                    self.t3.start()
                    self.index = self.index + 1
                    if self.index > 9:
                        self.index = 1
                    self.flag2 = False
        elif not self.F3 and not self.flag2:
                self.flag2 = True

        if self.Start:
            if self.flag3:
                self.index = 1
                print("restart")
                self.flag3 = False
        elif not self.flag3 and not self.Start:
                self.flag3 = True

        # if self.B:
        #     if self.t2 is None or not self.t2.is_alive():
        #         if self.flag2:
        #             self.t2 = threading.Thread(target=RobotInterface.cristmas_tree_event_voice, args=(self.index_fu,))
        #             self.t2 = threading.Thread(target=RobotInterface.give_hand)
        #             self.t2.start()
        #             self.index_fu = self.index_fu + 1
        #             if self.index_fu > 3:
        #                 self.index_fu = 1
        #             self.flag2 = False
        # elif not self.F3 and not self.flag2:
        #         self.flag2 = True

        if self.Up:
            if self.t2 is None or not self.t2.is_alive():
                if self.flag2:
                    self.t2 = threading.Thread(target=RobotInterface.requested_phrase, args=(1,))
                    self.t3 = threading.Thread(target=RobotInterface.cristmas_tree_event_action, args=(1,))
                    self.t2.start()
                    self.t3.start()
                    self.flag2 = False
        elif not self.Up and not self.flag2:
                self.flag2 = True
        
        if self.Right:
            if self.t2 is None or not self.t2.is_alive():
                if self.flag2:
                    self.t2 = threading.Thread(target=RobotInterface.requested_phrase, args=(2,))
                    self.t3 = threading.Thread(target=RobotInterface.cristmas_tree_event_action, args=(2,))
                    self.t2.start()
                    self.t3.start()
                    self.flag2 = False
        elif not self.Right and not self.flag2:
                self.flag2 = True

        if self.Down:
            if self.t2 is None or not self.t2.is_alive():
                if self.flag2:
                    self.t2 = threading.Thread(target=RobotInterface.requested_phrase, args=(3,))
                    self.t3 = threading.Thread(target=RobotInterface.cristmas_tree_event_action, args=(3,))
                    self.t2.start()
                    self.t3.start()
                    self.flag2 = False
        elif not self.Down and not self.flag2:
                self.flag2 = True

        if self.Left:
            if self.t2 is None or not self.t2.is_alive():
                if self.flag2:
                    self.t2 = threading.Thread(target=RobotInterface.requested_phrase, args=(4,))
                    self.t3 = threading.Thread(target=RobotInterface.cristmas_tree_event_action, args=(4,))
                    self.t2.start()
                    self.t3.start()
                    self.flag2 = False
        elif not self.Left and not self.flag2:
                self.flag2 = True

        if self.L1:
            if self.t4 is None or not self.t4.is_alive():
                if self.flag4:
                    self.t4 = threading.Thread(target=RobotInterface.right_kiss)
                    self.t4.start()
                    self.flag4 = False
            else:
                self.flag4 = True

        if self.R1:
            if self.t5 is None or not self.t5.is_alive():
                if self.flag5:
                    self.t5 = threading.Thread(target=RobotInterface.clap)
                    self.t5.start()
                    self.flag5 = False
            else:
                self.flag5 = True

        if self.Right:
            if self.t6 is None or not self.t6.is_alive():
                if self.flag6:
                    self.t6 = threading.Thread(target=RobotInterface.high_five)
                    self.t6.start()
                    self.flag6 = False
            else:
                self.flag6 = True
                
        if self.L2:
            if self.t7 is None or not self.t7.is_alive():
                if self.flag7:
                    self.t7 = threading.Thread(target=RobotInterface.hug)
                    self.t7.start()
                    self.flag7 = False
            else:
                self.flag7 = True

        if self.R2:
            if self.t8 is None or not self.t8.is_alive():
                if self.flag8:
                    self.t8 = threading.Thread(target=RobotInterface.x_ray)
                    self.t8.start()
                    self.flag8 = False
            else:
                self.flag8 = True 
            
        
class Custom:
    def __init__(self):
        self.low_state = None 
        self.remoteController = unitreeRemoteController()

    def Init(self):
        self.lowstate_subscriber = ChannelSubscriber("rt/lf/lowstate", LowState_)
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)

    
    def LowStateMessageHandler(self, msg: LowState_):
        self.low_state = msg
        wireless_remote_data = self.low_state.wireless_remote
        self.remoteController.parse(wireless_remote_data)

def main():
    ChannelFactoryInitialize(0, "eth0")
    custom = Custom()
    threading.Thread(target=custom.Init).start()
    while True:   
        time.sleep(1)

if __name__ == '__main__':
    main()
    

