# VoxType

**VoxType** is a free, privacy-first, fully local AI voice dictation and text transformation tool for Windows — inspired by commercial cloud apps like Wispr Flow.

It runs **100% on your own PC** using local GPU acceleration. No subscriptions, no cloud APIs, no data sent to external servers, and zero subscription costs.

---

## Why VoxType Was Created

Commercial cloud dictation services charge monthly subscription fees ($15+/month) and send your voice recordings to remote cloud servers for speech-to-text processing.

VoxType was created to give users complete control over their voice dictation:
- **100% Private**: Your voice never leaves your local hardware.
- **Completely Free**: Powered by open-source models on your local GPU.
- **Near-Zero Latency**: Real-time streaming GPU pre-processing with instant native clipboard injection.
- **Fully Customizable**: Choose between instant raw dictation or local LLM formatting, manage custom dictionaries, and customize prompts.

---

## Features

- **Instant Raw Dictation**: Powered by `faster-whisper` (`large-v3-turbo` model on CUDA INT8). Instant, accurate verbatim speech-to-text.
- **Optional AI Cleanup & Command Mode**: Optional Ollama integration (`llama3.2:3b` / `llama3.1:8b`) to clean up filler words ("um", "uh"), format markdown bullet lists, or transform selected text in-place.
- **System-Wide Global Hotkeys**:
  - `Ctrl + Win` — Press and hold to dictate, or double-tap to lock recording on.
  - `Ctrl + Win + Shift` — Command Mode (highlight text in any app, dictate a command, and transform it in-place).
  - `Ctrl + Win + S` — Instantly open/bring up the Control Dashboard GUI.
- **Automatic Background Audio Muting**: Mutes PC speaker playback (YouTube, Spotify, games) during dictation via Windows Core Audio (PyCAW) so background noise never interferes with recognition.
- **Pulsing Recording Overlay**: Floating frameless red dot indicator in the top-right corner of your screen during recording.
- **Control Dashboard GUI & History**: Minimalist white Qt dashboard to easily search past dictation history, toggle startup options, models, dictionaries, translation, gain boost, and sound cues.
- **Silent Background Execution**: Runs windowlessly in the background without any terminal/console taskbar window.
- **Windows Startup Support**: One-click toggle to launch automatically when Windows boots up.

---

## Prerequisites

- **OS**: Windows 10 or Windows 11 (64-bit)
- **Python**: Python 3.10+ (tested on Python 3.14)
- **GPU**: NVIDIA GPU with CUDA support (e.g. RTX 3060, 4070, 5070 Ti, etc.). *CPU fallback is supported automatically.*
- **Ollama** *(Optional — for Command Mode & AI Cleanup)*: Download from [ollama.com](https://ollama.com).

---

## Quick Start & Installation

### 1. Clone the Repository
```cmd
git clone https://github.com/gitedmond/voxtype.git
cd voxtype
```

### 2. Set Up Virtual Environment & Dependencies
```cmd
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 3. (Optional) Pull Ollama Model for Command Mode
```cmd
ollama pull llama3.2:3b
```

### 4. Launch VoxType Windowlessly
Double-click `run_silent.vbs` (or `run.bat`) to launch VoxType silently in the background with zero terminal windows.

---

## Usage Guide

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl + Win` (Hold) | **Hold-to-Talk Dictation** | Speak while holding the keys. Release to instantly paste text at your cursor. |
| `Ctrl + Win` (Double-Tap) | **Lock Recording Mode** | Tap twice to lock recording ON. Tap once more when done speaking to paste. |
| `Ctrl + Win + Shift` | **Command Mode** | Select text in any app, hold hotkey, and state a command. |
| Double-click `run_silent.vbs` | **Re-open Dashboard** | Double-clicking `run_silent.vbs` or `run.bat` at any time re-opens the Dashboard. |
| System Tray Icon | **Taskbar System Tray** | Click the VoxType icon in the Windows notification area (`^`) to open Dashboard. |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         VoxType Engine                           │
├──────────────┬──────────────┬──────────────────┬─────────────────┤
│ Input        │ ASR Engine   │ Audio Controller │ Text Injection  │
│              │              │                  │                 │
│ pynput       │ faster-      │ PyCAW            │ Windows         │
│ Global       │ whisper      │ Master Volume    │ keybd_event     │
│ Hotkeys      │ CUDA INT8    │ Speaker Muting   │ Clipboard Paste │
├──────────────┴──────────────┴──────────────────┴─────────────────┤
│ PySide6 Control Dashboard GUI & System Tray Integration          │
└──────────────────────────────────────────────────────────────────┘
```

---

## License

Distributed under the [MIT License](LICENSE).
