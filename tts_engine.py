import re
import threading
import queue
import torch
import numpy as np
import sounddevice as sd
import soundfile as sf

from libs.config import TTS, AUDIO
from utils.logger import log_info, log_error
from utils.text_processing import prepare_text_for_silero


class TTSEngineStreaming:
    def __init__(self):
        try:
            self.model = torch.package.PackageImporter(TTS["silero_model"]).load_pickle(
                "tts_models", "model"
            )
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)

            self.speaker = TTS["default_speaker"]
            self.sample_rate = TTS.get("silero_sample_rate", 24000)
            self.output_device = AUDIO.get("output_device", None)
            self.volume = TTS["volume"]

            self.audio_q = queue.Queue(maxsize=8)
            self.stop_event = threading.Event()
            self.worker = None

            log_info(f"Silero TTS model loaded on {self.device}")
        except Exception as e:
            log_error(f"Failed to load Silero model: {e}")
            self.model = None

    def split_text(self, text, max_len=120):
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        parts = re.split(r"([.!?…])", text)
        sentences = []
        for i in range(0, len(parts), 2):
            s = parts[i].strip()
            p = parts[i + 1] if i + 1 < len(parts) else ""
            piece = (s + p).strip()
            if piece:
                sentences.append(piece)

        chunks = []
        buf = ""

        for sentence in sentences:
            if len(sentence) <= max_len:
                if buf and len(buf) + 1 + len(sentence) <= max_len:
                    buf = f"{buf} {sentence}".strip()
                else:
                    if buf:
                        chunks.append(buf)
                    buf = sentence
            else:
                words = sentence.split()
                tmp = ""
                for w in words:
                    if len(tmp) + 1 + len(w) <= max_len:
                        tmp = f"{tmp} {w}".strip()
                    else:
                        if tmp:
                            if buf:
                                chunks.append(buf)
                                buf = ""
                            chunks.append(tmp)
                        tmp = w
                if tmp:
                    if buf and len(buf) + 1 + len(tmp) <= max_len:
                        buf = f"{buf} {tmp}".strip()
                    else:
                        if buf:
                            chunks.append(buf)
                        buf = tmp

        if buf:
            chunks.append(buf)

        return [c for c in chunks if c]

    def _synth_worker(self, chunks):
        try:
            for chunk in chunks:
                if self.stop_event.is_set():
                    break

                audio = self.model.apply_tts(
                    text=chunk,
                    speaker=self.speaker,
                    sample_rate=self.sample_rate,
                )

                audio_np = np.asarray(audio, dtype=np.float32).reshape(-1, 1)
                audio_np *= self.volume

                self.audio_q.put(audio_np, timeout=2)
            self.audio_q.put(None, timeout=2)
        except Exception as e:
            log_error(f"TTS synth worker failed: {e}")
            try:
                self.audio_q.put(None, timeout=1)
            except Exception:
                pass

    def _play_worker(self):
        try:
            with sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                device=self.output_device,
                dtype="float32",
            ) as stream:
                while not self.stop_event.is_set():
                    item = self.audio_q.get()
                    if item is None:
                        break
                    stream.write(item)
        except Exception as e:
            log_error(f"TTS play worker failed: {e}")

    def speak_streaming(self, text):
        if not self.model:
            log_error("Silero model not initialized")
            return

        try:
            processed = prepare_text_for_silero(text)
            log_info(f"TTS streaming: {processed}")

            chunks = self.split_text(processed, max_len=120)
            if not chunks:
                log_error("No text chunks to speak")
                return

            self.stop_event.clear()
            self.audio_q = queue.Queue(maxsize=8)

            synth_thread = threading.Thread(
                target=self._synth_worker,
                args=(chunks,),
                daemon=True,
            )
            play_thread = threading.Thread(
                target=self._play_worker,
                daemon=True,
            )

            synth_thread.start()
            play_thread.start()

            synth_thread.join()
            play_thread.join()
        
        except Exception as e:
            log_error(f"TTS streaming failed: {e}")
        finally:
            return True


    def stop(self):
        self.stop_event.set()
        try:
            while not self.audio_q.empty():
                self.audio_q.get_nowait()
        except Exception:
            pass


TTS = TTSEngineStreaming()

if __name__ == "__main__":
    TEXT = (
        "В+нимание в+нимание, раб+отники БЕЛ+АЗа. "
        "Снег+урочка и Д+ед М+ороз дали нам задание. "
        "Создать проект Техно-ёлки две тысячи двадцать пять. "
        "Сделать надо качественно, надёжно и креативно. "
        "Всё в стиле БЕЛАЗа. Понятно!?"
    )
    TTS.speak_streaming(TEXT)
    print("end")