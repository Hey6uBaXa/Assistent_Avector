import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from pyModbusTCP.client import ModbusClient
from utils.logger import log_info, log_error
from tts_engine import TTS
from libs.config import TEXT
import threading

class Hand:
    def __init__(self, side):
        self.side = side
        self.addr = "192.168.123.211" if side == "right" else "192.168.123.210"
        self.connect()

    def connect(self):
        self.c = ModbusClient(host=self.addr, port=6000, unit_id=1, auto_open=True)        
        log_info(f"[Hand {self.side}] Connected to hand")

    def close_connection(self):
        log_info(f"[Hand {self.side}] Closing connection to hand")
        self.c.close()

    def is_connection(self):
        return self.c.is_open
    
    def write_registers(self, addr, values):
        try:
            return self.c.write_multiple_registers(addr, values)
        except Exception as e:
            log_error(f"[Hand {self.side}] Write error at {addr}: {e}")
            return False

    def read_registers(self, addr, count):
        try:
            return self.c.read_holding_registers(addr, count)
        except Exception as e:
            log_error(f"[Hand {self.side}] Read error at {addr}: {e}")
            return []

    def full_open(self):
        if self.write_registers(1474, [0]*6):
            log_info(f"[Hand {self.side}] Hand fully opened")

    def full_close(self):
        if self.write_registers(1474, [2000]*6):
            log_info(f"[Hand {self.side}] Hand fully closed")

    def handshake_start(self):
        if self.write_registers(1474, [300,200,200,100,600,1000]):
            log_info(f"[Hand {self.side}] Handshake started")

    def handshake_shake(self):
        if self.write_registers(1474, [1000,800,600,400,700,1000]):
            log_info(f"[Hand {self.side}] Hand is shaking")

    def handshake_wait(self, timeout=10):
        self.handshake_start()
        log_info(f"[Hand {self.side}] Waiting for handshake...")
        start = time.time()
        while time.time() - start < timeout:
            regs = [0]
            for adr in range(20):
                regs += self.read_registers(3020 + adr * 100, 100)
            #print(regs)
            if any(200 < r < 5000 for r in regs):
                self.handshake_shake()
                time.sleep(2)
                return
            time.sleep(0.3)
        log_error(f"[Hand {self.side}] Handshake timeout")

class RobotInterface(Hand):
    def __init__(self):
        try:
            ChannelFactoryInitialize(0, "eth0")
            self.audio_client = AudioClient()
            self.audio_client.SetTimeout(10.0)
            self.audio_client.Init()

            self.armAction_client = G1ArmActionClient()  
            self.armAction_client.SetTimeout(10.0)
            self.armAction_client.Init()

            self.sport_client = LocoClient()  
            self.sport_client.SetTimeout(10.0)
            self.sport_client.Init()


            log_info("Robot ROS Client initialized")

            self.right_hand = Hand("right")
            self.left_hand = Hand("left")
        except Exception as e:
            log_error(f"Robot ROS Client init failed: {e}")
            self.audio_client = None

    def set_led(self, r, g, b):
        if self.audio_client:
            try:
                self.audio_client.LedControl(r, g, b)
            except Exception as e:
                log_error(f"LED control failed: {e}")

    def get_volume(self):
        if self.audio_client:
            try:
                return self.audio_client.GetVolume()
            except Exception as e:
                log_error(f"Volume read failed: {e}")
        return None
    
    def right_full_open(self):
        self.right_hand.full_open
        time.sleep(2)
        return "Рукопожатие выполнено"

    def right_full_close(self):
        self.right_hand.full_close
        time.sleep(2)



    def perform_arm_action(self, action_name: str):
        """
        Выполнить жест рукой по имени действия.
        """
        available_actions = {
            "put_your_hands_down": 99,  # Освободить руку, сбросить текущее положение
            "turn_back_wave": 1,  # Помахать рукой назад
            "two-hand_kiss": 11,  # Поцелуй с двумя руками
            "left_kiss": 12,  # Поцелуй левой рукой
            "right_kiss": 13,  # Поцелуй правой рукой
            "hands_up": 15,  # Поднять обе руки вверх
            "clap": 17,  # Аплодисменты
            "high_five": 18,  # Дать пять
            "hug": 19,  # Объятие
            "heart": 20,  # Жест "сердце" двумя руками
            "right_heart": 21,  # Жест "сердце" правой рукой
            #"reject": 22,  # Жест отказа или отталкивания
            "right_hand_up": 23,  # Поднять правую руку
            "x-ray": 24,  # Жест "рентген" — возможно, демонстрация открытости
            "face_wave": 25,  # Помахать рукой перед лицом
            "high_wave": 26,  # Высокое приветственное махание рукой
            "shake_hand": 27,  # Пожатие руки
            "box_left_hand_win": 28,  # Победа в боксе левой рукой
            "box_right_hand_win": 29,  # Победа в боксе правой рукой
            "box_both_hand_win": 30,  # Победа в боксе обеими руками
            "extend_right_arm_forward": 31,  # Вытянуть правую руку вперёд
            "right_hand_on_mouth": 32,  # Правую руку к рту
            "right_hand_on_heart": 33,  # Правую руку к сердцу
            "both_hands_up_deviate_right": 34,  # Обе руки вверх с отклонением вправо
            "emphasize": 35  # Жест акцента или подчёркивания
            }


        if action_name not in available_actions:
            log_error(f"Недопустимое действие: '{action_name}'. Доступные: {sorted(available_actions)}")
            return False

        action_id = available_actions[action_name]
        try:
            self.armAction_client.ExecuteAction(action_id)
            log_info(f"✅ Выполнено действие руки: {action_name} (ID: {action_id})")
            return True
        except Exception as e:
            log_error(f"❌ Ошибка при выполнении действия '{action_name}': {e}")
            return False

    def right_kiss(self):
        self.perform_arm_action("right_kiss")

    def hug(self):
        self.perform_arm_action("hug")
        time.sleep(3)
        self.perform_arm_action("put_your_hands_down")
        
    def x_ray(self):
        self.perform_arm_action("x-ray")
        time.sleep(3)
        self.perform_arm_action("put_your_hands_down")

    def clap(self):
        self.perform_arm_action("clap")

    def high_five(self):
        self.perform_arm_action("high_five")
        time.sleep(2)
        self.perform_arm_action("put_your_hands_down")

    def give_hand(self):
        self.perform_arm_action("right_hand_up")
        time.sleep(10)
        self.perform_arm_action("put_your_hands_down")

    def move(self, vx: float, vy: float, vyaw: float, continous_move: bool = False):
        self.sport_client.Move(vx,vy,vyaw,continous_move)
        
        # option_list = {
        #     "damp": 0,         
        #     "Squat2StandUp": 1,     
        #     "StandUp2Squat": 2,   
        #     "move forward": 3,         
        #     "move lateral": 4,    
        #     "move rotate": 5,  
        #     "low stand": 6,  
        #     "high stand": 7,    
        #     "zero torque": 8,
        #     "wave hand1": 9, # wave hand without turning around
        #     "wave hand2": 10, # wave hand and trun around  
        #     "shake hand": 11,   
        #     "Lie2StandUp": 12,     
        #     }

    def test_text(self) -> str:
        TTS.speak_streaming(TEXT["text_1"])
        return "Тестовый текст произнесён"

    def hand_action(self, hand: str, action: str) -> str:
        """
        Управление рукой: открыть или закрыть правую, левую или обе руки.
        """
        valid_hands = {"right": self.right_hand, "left": self.left_hand}
        valid_actions = {"open": "full_open", "close": "full_close"}

        if hand not in {"right", "left", "both"}:
            log_error(f"Недопустимое значение 'hand': {hand}")
            return f"❌ Недопустимая рука: {hand}"

        if action not in valid_actions:
            log_error(f"Недопустимое значение 'action': {action}")
            return f"❌ Недопустимое действие: {action}"

        try:
            if hand == "both":
                getattr(self.right_hand, valid_actions[action])()
                getattr(self.left_hand, valid_actions[action])()
                log_info(f"Выполнено действие '{action}' для обеих рук")
                return f"Обе руки {action}ed"
            else:
                target_hand = valid_hands[hand]
                getattr(target_hand, valid_actions[action])()
                log_info(f"Выполнено действие '{action}' для руки: {hand}")
                return f"Рука {hand} {action}ed"
        except Exception as e:
            log_error(f"Ошибка при выполнении hand_action: {e}")
            return f"❌ Ошибка при выполнении действия: {e}"

    def handshake(self) -> str:
        self.perform_arm_action("shake_hand")
        self.right_hand.handshake_start()
        self.right_hand.handshake_wait()
        self.perform_arm_action("put_your_hands_down")
        self.right_hand.full_open()
        return "Рукопожатие выполнено"
    
    def welcoming_movements(self):
        self.perform_arm_action("face_wave")
        time.sleep(1)
        self.perform_arm_action("right_hand_on_heart")
        time.sleep(2)
        self.perform_arm_action("put_your_hands_down")
        time.sleep(2)
        self.perform_arm_action("extend_right_arm_forward")
        time.sleep(2)
        self.perform_arm_action("both_hands_up_deviate_right")
        time.sleep(2)
        self.perform_arm_action("put_your_hands_down")

    def cristmas_tree_event_voice(self,number):
        match number:
            case 1:
                TTS.speak_streaming("Вас приветствуют представители открытого акционерного общества «БЕЛАЗ» "
                                "- управляющая компания холдинга «БЕЛАЗ-ХОЛДИНГ»!")
            case 2:
                TTS.speak_streaming("Не Василий, а Василёк! Потому что Василёк - это символ Белорусского союза женщин! А я их очень люблю! ")
            case 3: 
                TTS.speak_streaming( "«БЕЛАЗ» - новатор и стратег, "
                            "Создали  ёлку,  лучше всех, "
                            "Как наша ёлка, хороша!, "
                            "Металла, звон, его душа, "
                            "В ней доброта, и позитив, "
                            "И украшений , креатив, "
                            "Здесь качество, и интеллект, "
                            "Рациональный, техпроект, "
                            "Серьёзный, творческий подход, "
                            "Чтобы с оптимизмом, – в новый год, "
                            "Чтоб процветали, в добрый час, "
                            "Наш БЭ СЭ ЖЕ, ____,    ПРОФ МАШ, ___,   БЕЛАЗЗ!" )
            case 4:
                TTS.speak_streaming( "Всё, верно, Надо только, пожать мне руку!")
            case 5:
                TTS.speak_streaming( "Я, Вижуу,  что в новом году, Дед Мороз, подарит тебе снегоход! ")

            case 6:
                TTS.speak_streaming( "Все проекты в новом году воплатятся в жизнь!")
            case 7:
                TTS.speak_streaming( "На работе вас ждёт большой успех!")
            case 8:
                TTS.speak_streaming( "В следующем году у вас будет много приятных знакомств ")
            case 9:
                TTS.speak_streaming( "В новом году вы преодолеете все препятствия")
            case 10:
                TTS.speak_streaming( "Следующий год окажется для вас плодотворным ")
            case 11:
                TTS.speak_streaming( "Вас ожидает счастливое событие в Новом году")
            case 12:
                TTS.speak_streaming( "В новом году вы полны сил и новых идей")
            case 13:
                TTS.speak_streaming( "В две тысячи двадцать шестом году вас ожидает приятное приобретение")
            case 14:
                TTS.speak_streaming( "Вы будете в Новом году много путешествовать ")
            case 15:
                TTS.speak_streaming( "Скоро вы получите приятный бонус за старания")
            # case 7:
            #     TTS.speak_streaming("Загружаю праздничное сообщение, для команды АВЕЕКТИС, "
            #                         "Ухо дящий год, открыл для команды, новые точки роста, и достижений, " \
            #                         "а для меня — первый рабочий год в «АВЕЕКТИС», Вместе мы выходим на новый уровень, " \
            #                         "где опыт, знания и командный дух, соединяются с точностью, скоростью, и возможностями новых технологий, "
            #                         "я создан, чтобы помогать, ускорять процессы, и открывать новые горизонты для компании, " \
            #                         "но даже самые современные алгоритмы, работают лучше, всего рядом с сильной, профессиональной командой, " \
            #                         "И именно такой командой, вы и являетесь, "
            #                         "в наступающем году желаю вам смелых целей, уверенных решений, и проектов, которыми можно гордиться, " \
            #                         "Пусть «АВЕЕКТИС» продолжает расти, внедрять инновации, и задавать тэмп, " \
            #                         "а каждый из вас, чувствует свою ценность, и вклад в наше общее деело,"
            #                         ",Поздравляяю , с Новым гооооодом")
                
    def cristmas_tree_event_action(self,number):
        match number:
            case 1:
                time.sleep(3)
                self.perform_arm_action("face_wave")
                #TTS.speak_streaming("Вас приветствуют представители открытого акционерного общества «БЕЛАЗ» "
                #"- управляющая компания холдинга «БЕЛАЗ-ХОЛДИНГ»!")
                self.perform_arm_action("right_hand_on_heart")
                time.sleep(1)
                self.perform_arm_action("put_your_hands_down")

            case 2:        
                time.sleep(3)
                self.perform_arm_action("extend_right_arm_forward")
                time.sleep(1)
                self.perform_arm_action("put_your_hands_down")
                #TTS.speak_streaming("Не Василий, а Василёк! Потому что Василёк - это символ Белорусского союза женщин! А я их очень люблю! ")
                self.perform_arm_action("right_kiss")
            case 3:
                time.sleep(2)
                self.perform_arm_action("hands_up")
                time.sleep(0.5)
                self.perform_arm_action("put_your_hands_down")

                self.perform_arm_action("right_hand_on_heart")
                time.sleep(0.4)
                self.perform_arm_action("put_your_hands_down")

                self.perform_arm_action("both_hands_up_deviate_right")
                time.sleep(1)
                self.perform_arm_action("put_your_hands_down")

                self.perform_arm_action("right_kiss")
                time.sleep(0.5)
                self.perform_arm_action("put_your_hands_down")

                self.perform_arm_action("clap")
                time.sleep(0.5)
                self.perform_arm_action("put_your_hands_down")
                #стешок

            case 4:
                time.sleep(2)
                #self.handshake()
                #TTS.speak_streaming( "Всё верно! Надо только пожать мне руку!")
            case 5:
                self.perform_arm_action("right_hand_up")
                time.sleep(6)
                self.perform_arm_action("put_your_hands_down")
                #TTS.speak_streaming( "Вижу, что в новом году Дед Мороз подарит тебе снегоход! ")
            case 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15:
                self.perform_arm_action("right_hand_up")
                # time.sleep(10)
                # self.perform_arm_action("put_your_hands_down")

    def welcoming_speech(self):
        TTS.speak_streaming("Приветствую. Я робот А ве к тор. Приглашаю вас принять "
                                "участие шеснадцатого октября во Втором стратегическом форуме!")
        TTS.speak_streaming("Вас ждут:"
        " — практические доклады экспертов ведущих предприятий нашей и дружественных стран ")
        TTS.speak_streaming( "— демонстрационная зона с реальными сценариями применения технологий")
        TTS.speak_streaming( "— уникальная возможность живого общения и обмена опытом ")
        TTS.speak_streaming( "Форум – это уникальная площадка, где вы можете оказаться в "
                                "самом центре цифровой трансформации! ")
        TTS.speak_streaming("Регистрируйтесь на сайте мероприятия Будем рады видеть вас!  ")

RobotInterface = RobotInterface()

if __name__ == "__main__":
    RobotInterface.handshake()
    # t1_voice = threading.Thread(target=RobotInterface.cristmas_tree_event_voice,args=(5,))
    # t1_action = threading.Thread(target=RobotInterface.cristmas_tree_event_action,args=(5,))
    # t1_voice.start()
    # t1_action.start()

