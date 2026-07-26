import queue
import numpy as np
import sounddevice as sd

def list_audio_input_devices() -> list[dict]:
    """Query available audio input devices (microphones) on Windows."""
    devices = []
    try:
        all_devices = sd.query_devices()
        for idx, dev in enumerate(all_devices):
            if dev.get("max_input_channels", 0) > 0:
                devices.append({
                    "index": idx,
                    "name": dev.get("name", f"Device {idx}"),
                    "channels": dev.get("max_input_channels", 1),
                    "default_samplerate": dev.get("default_samplerate", 16000)
                })
    except Exception as e:
        print(f"[AudioRecorder] Error listing input devices: {e}")
    return devices

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, device_index: int | None = None, gain: float = 1.0):
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.gain = max(0.5, float(gain))
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start(self) -> None:
        self._queue = queue.Queue()
        kwargs = {
            "samplerate": self.sample_rate,
            "channels": 1,
            "dtype": "float32",
            "callback": self._callback,
        }
        if self.device_index is not None:
            kwargs["device"] = self.device_index

        try:
            self._stream = sd.InputStream(**kwargs)
            self._stream.start()
            self._is_recording = True
            dev_str = f"device #{self.device_index}" if self.device_index is not None else "default device"
            print(f"[AudioRecorder] Started recording on {dev_str} (Gain: {self.gain:.1f}x).")
        except Exception as e:
            print(f"[AudioRecorder] Error opening audio input device ({e}), falling back to default device...")
            kwargs.pop("device", None)
            self._stream = sd.InputStream(**kwargs)
            self._stream.start()
            self._is_recording = True

    def _apply_gain(self, audio: np.ndarray) -> np.ndarray:
        """Apply software gain boost for low-volume whispered speech with clipping protection."""
        if self.gain != 1.0 and len(audio) > 0:
            return np.clip(audio * self.gain, -1.0, 1.0)
        return audio

    def get_current_snapshot(self) -> np.ndarray:
        """Return a copy of all audio recorded so far without stopping or draining the queue."""
        if not self._is_recording:
            return np.array([], dtype=np.float32)

        with self._queue.mutex:
            chunks = list(self._queue.queue)

        if not chunks:
            return np.array([], dtype=np.float32)
        raw = np.concatenate(chunks, axis=0).flatten()
        return self._apply_gain(raw)

    def stop(self) -> np.ndarray:
        self._is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        chunks = []
        while not self._queue.empty():
            chunks.append(self._queue.get())
        print("[AudioRecorder] Stopped recording.")
        if not chunks:
            return np.array([], dtype=np.float32)
        raw = np.concatenate(chunks, axis=0).flatten()
        return self._apply_gain(raw)

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            print(f"[AudioRecorder] Warning status: {status}")
        self._queue.put(indata.copy())
