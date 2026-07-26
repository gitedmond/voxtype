import os
import sys
import numpy as np

def setup_cuda_dll_paths():
    """Register NVIDIA pip package DLL directories on Windows for ctranslate2 / CUDA."""
    if sys.platform == "win32":
        site_packages = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
        if os.path.exists(site_packages):
            for root, dirs, _ in os.walk(site_packages):
                if "bin" in dirs or "lib" in dirs:
                    dll_dir = os.path.join(root, "bin") if "bin" in dirs else os.path.join(root, "lib")
                    try:
                        os.add_dll_directory(dll_dir)
                        os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")
                    except Exception:
                        pass

setup_cuda_dll_paths()

from faster_whisper import WhisperModel

class ASREngine:
    def __init__(self, model_name: str = "large-v3-turbo",
                 compute_type: str = "int8", device: str = "cuda",
                 language: str | None = None):
        self.model_name = model_name
        self.compute_type = compute_type
        self.device = device
        self.language = language
        self._initial_prompt: str = ""
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        print(f"[ASR] Loading Whisper model '{self.model_name}' on {self.device} ({self.compute_type})...")
        try:
            self.model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
            print("[ASR] Model loaded successfully on GPU.")
        except Exception as e:
            print(f"[ASR] GPU load failed ({e}), attempting CPU fallback...")
            self.device = "cpu"
            self.compute_type = "int8"
            self.model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            print("[ASR] Model loaded successfully on CPU.")

    def set_dictionary(self, terms: list[str]) -> None:
        self._initial_prompt = ", ".join(terms) if terms else ""
        print(f"[ASR] Updated initial prompt vocabulary: '{self._initial_prompt}'")

    def transcribe(self, audio: np.ndarray, verbose: bool = True) -> str:
        if len(audio) == 0:
            return ""
        if self.model is None:
            self._load_model()

        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            initial_prompt=self._initial_prompt or None,
            vad_filter=False,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        if verbose:
            print(f"[ASR] Raw transcript ({info.language}): '{text}'")
        return text
