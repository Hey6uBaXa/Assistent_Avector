import sounddevice as sd
from libs.config import INPUT
def test_samplerate(device, samplerate, channels=1):
    try:
        sd.check_input_settings(device=device, samplerate=samplerate, channels=channels)
        return True
    except Exception:
        return False

def supported_samplerates(device, rates, channels=1):
    ok = []
    for r in rates:
        if test_samplerate(device, r, channels=channels):
            ok.append(r)
    return ok

rates = [8000, 16000, 22050, 24000, 32000, 44100, 48000, 96000, 192000]
device_index = INPUT  # твой индекс input-устройства

print(supported_samplerates(device_index, rates, channels=1))