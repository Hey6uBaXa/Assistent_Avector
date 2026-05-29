import queue
import json
import time
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from libs.config import AUDIO, STT
from utils.logger import log_info, log_error
from robot_interface import RobotInterface
import numpy as np

class LEDController:
    def __init__(self):
        self.current_brightness = 0  # текущая яркость (0–255)
        self.decay = 0.9             # скорость затухания (меньше = дольше тлеет)
        self.threshold = 40         # порог громкости (подбери под свой микрофон)

    def update(self, level):
        if level < self.threshold:
            # при звуке сразу на максимум
            self.current_brightness = 255
        else:
            # плавное затухание
            self.current_brightness = int(self.current_brightness * (1 - self.decay))

        if self.current_brightness < 50:
            self.current_brightness = 50
        # отправляем в светодиод
        RobotInterface.set_led(r=self.current_brightness, g=0, b=self.current_brightness)

led = LEDController()

class STTEngine:
    def __init__(self):
        self.q = queue.Queue()
        self.model_lang = "ru"
        self.model = self.load_model(self.model_lang)
        self.rec = KaldiRecognizer(self.model, AUDIO["sample_rate"])
        self.stream = None
        self.paused = False
        self._start_stream()

        self.led_brightness = 0
        self.last_update = time.time()

    def load_model(self, lang):
        try:
            path = STT["vosk_model_ru"] if lang == "ru" else STT["vosk_model_en"]
            log_info(f"Loading Vosk model: {path}")
            return Model(path)
        except Exception as e:
            log_error(f"Failed to load Vosk model for '{lang}': {e}")
            return None

    def callback(self, indata, frames, time_info, status):
        if status:
            log_error(f"STT stream status: {status}")

        # 🎤 громкость блока (RMS)
        audio_data = np.frombuffer(indata, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_data**2))

        # обновляем LED
        led.update(rms)

        # передаём данные для распознавания
        if not self.paused:
            self.q.put(bytes(indata))

    def _start_stream(self):
        try:
            self.stream = sd.RawInputStream(
                samplerate=AUDIO["sample_rate"],
                blocksize=AUDIO["block_size"],
                dtype='int16',
                channels=AUDIO["channels"],
                device=AUDIO["input_device"],
                callback=self.callback
            )
            self.stream.start()
            log_info("STT stream started")
        except Exception as e:
            log_error(f"STT stream start failed: {e}")
            self.stream = None

    def listen(self, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            try:
                data = self.q.get(timeout=0.5)
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get("text", "").strip().lower()
                    if text:
                        log_info(f"STT result: {text}")
                    return text
            except queue.Empty:
                continue
            except Exception as e:
                log_error(f"STT listen error: {e}")
                return ""
        log_info("STT listen timeout")
        return ""

    def pause(self):
        self.paused = True
        RobotInterface.set_led(r=0, g=0, b=255)
        log_info("STT stream paused")

    def resume(self):
        self.paused = False
        log_info("STT stream resumed")

    def language_switch(self, lang):
        if lang != self.model_lang:
            log_info(f"Switching STT language: {self.model_lang} → {lang}")
            self.pause()
            self.model_lang = lang
            self.model = self.load_model(lang)
            self.rec = KaldiRecognizer(self.model, AUDIO["sample_rate"])
            self.resume()

STT = STTEngine()

if __name__ == "__main__":
    print("start")
    while True:
        print("listen")
        text = STT.listen()

        if text:
            STT.pause()
            print(f"📝 Распознано: {text}")
            STT.resume()