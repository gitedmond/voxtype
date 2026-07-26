import os
import winsound
import numpy as np
import scipy.io.wavfile as wavfile

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "sounds")

def ensure_sounds_exist():
    os.makedirs(SOUNDS_DIR, exist_ok=True)
    start_path = os.path.join(SOUNDS_DIR, "start.wav")
    stop_path = os.path.join(SOUNDS_DIR, "stop.wav")

    sample_rate = 22050
    duration = 0.08  # 80ms beep

    if not os.path.exists(start_path):
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = 0.3 * np.sin(2 * np.pi * 880 * t)
        env = np.hanning(len(audio))
        audio_int16 = (audio * env * 32767).astype(np.int16)
        wavfile.write(start_path, sample_rate, audio_int16)

    if not os.path.exists(stop_path):
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = 0.3 * np.sin(2 * np.pi * 523.25 * t)
        env = np.hanning(len(audio))
        audio_int16 = (audio * env * 32767).astype(np.int16)
        wavfile.write(stop_path, sample_rate, audio_int16)

def play_sound(filename: str) -> None:
    ensure_sounds_exist()
    path = os.path.join(SOUNDS_DIR, filename)
    if os.path.exists(path):
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:
            print(f"[Sound] Error playing {filename}: {e}")
