import time
import threading
from stt_engine import STT
from tts_engine import TTS
from OllamaClient import LLM_Client
from robot_interface import RobotInterface
from libs.config import DIALOG
from utils.logger import log_info, log_error
from test_wireless import main

RobotInterface.set_led(r=0, g=0, b=255)

# 🔁 Диалоговое состояние
activation_phrases = DIALOG["activation_phrases"]
dialog_timeout = DIALOG["timeout"]

def should_activate(text):
    return any(phrase in text.lower() for phrase in activation_phrases)

def passive_listen_loop():
    """Пассивное прослушивание для активации"""
    STT.resume()
    while True:
        text = STT.listen(timeout=4)  # короткие фрагменты
        if not text:
            continue

        log_info(f"[Пассивное прослушивание] Распознано: {text}")
        if should_activate(text):
            log_info("🔊 Ключевая фраза найдена. Активация.")
            STT.pause()
            threading.Thread(target=active_dialog_loop).start()
            #active_dialog_loop()
            break  # остановить пассивное прослушивание

def active_dialog_loop():
    """Активный режим диалога после активации"""
    TTS.speak_streaming("Я слушаю")
    RobotInterface.set_led(r=0, g=255, b=0)
    try:
        STT.resume()
        text = STT.listen(timeout=dialog_timeout)
        if text:
            log_info(f"[Активный режим] Пользователь сказал: {text}")
            STT.pause()
            reply = LLM_Client.ask(text)
            TTS.speak_streaming(reply)
    except Exception as e:
        log_error(f"Ошибка в active_dialog_loop: {e}")
    finally:
        RobotInterface.set_led(r=0, g=0, b=255)
        time.sleep(1)
        
        passive_listen_loop()  # вернуться к пассивному режиму

if __name__ == "__main__":
    threading.Thread(target=main).start()
    try:
        passive_listen_loop()
    except KeyboardInterrupt:
        log_info("Ассистент остановлен вручную")
    except Exception as e:
        log_error(f"Ошибка в passive_listen_loop: {e}")
