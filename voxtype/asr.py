import os
import sys
import gc
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
                 language: str | None = None, translate_mode: bool = False):
        self.model_name = model_name
        self.compute_type = compute_type
        self.device = device
        self.language = language
        self.translate_mode = translate_mode
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

    def unload_model(self) -> None:
        """Unload Whisper model from GPU memory to free up VRAM when idle."""
        if self.model is not None:
            print("[ASR] Unloading Whisper model from GPU VRAM...")
            del self.model
            self.model = None
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def set_dictionary(self, terms: list[str]) -> None:
        self._initial_prompt = ", ".join(terms) if terms else ""
        print(f"[ASR] Updated initial prompt vocabulary: '{self._initial_prompt}'")

    def transcribe(self, audio: np.ndarray, verbose: bool = True) -> str:
        if len(audio) == 0:
            return ""
        if self.model is None:
            print("[ASR] Model was unloaded, reloading into GPU VRAM for dictation...")
            self._load_model()

        task = "translate" if self.translate_mode else "transcribe"

        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            task=task,
            initial_prompt=self._initial_prompt or None,
            vad_filter=False,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        if verbose:
            mode_label = "Translation (->en)" if task == "translate" else f"Raw transcript ({info.language})"
            print(f"[ASR] {mode_label}: '{text}'")
        return text
