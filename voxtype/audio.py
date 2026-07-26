import queue
import numpy as np
import sounddevice as sd

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start(self) -> None:
        self._queue = queue.Queue()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()
        self._is_recording = True
        print("[AudioRecorder] Started recording.")

    def get_current_snapshot(self) -> np.ndarray:
        """Return a copy of all audio recorded so far without stopping or draining the queue."""
        if not self._is_recording:
            return np.array([], dtype=np.float32)

        with self._queue.mutex:
            chunks = list(self._queue.queue)

        if not chunks:
            return np.array([], dtype=np.float32)
        return np.concatenate(chunks, axis=0).flatten()

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
        return np.concatenate(chunks, axis=0).flatten()

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            print(f"[AudioRecorder] Warning status: {status}")
        self._queue.put(indata.copy())
