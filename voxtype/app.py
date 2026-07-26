import sys
import time
import ctypes
import socket
import threading
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QObject, Signal

from voxtype.config import load_config, VoxTypeConfig
from voxtype.audio import AudioRecorder
from voxtype.asr import ASREngine
from voxtype.llm import LLMEngine
from voxtype.injector import TextInjector
from voxtype.hotkeys import HotkeyManager
from voxtype.overlay import RecordingOverlay
from voxtype.settings_window import SettingsWindow
from voxtype.sound_utils import play_sound
from voxtype.audio_muter import AudioMuter
from voxtype.history import HistoryManager

IPC_PORT = 49812

class AppBridge(QObject):
    signal_open_dashboard = Signal()

def check_single_instance_or_trigger_dashboard() -> bool:
    """
    Check if VoxType is already running. If so, send OPEN_DASHBOARD signal to
    the running instance via localhost socket so it re-opens its window, then return True.
    """
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(0.5)
        client.connect(("127.0.0.1", IPC_PORT))
        client.sendall(b"OPEN_DASHBOARD")
        client.close()
        print("[VoxType] An instance is already running. Re-opened Control Dashboard GUI.")
        return True
    except Exception:
        return False

def create_tray_icon_pixmap() -> QPixmap:
    """Create a clean 32x32 icon for the system tray."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer circle
    painter.setBrush(QColor(0, 122, 255))  # iOS Blue
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)

    # Microphone / 'V' emblem in center
    painter.setPen(QColor(255, 255, 255))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "V")
    painter.end()
    return pix

class VoxTypeApp:
    def __init__(self):
        print("[VoxType] Initializing application...")
        self.config: VoxTypeConfig = load_config()

        # Initialize Qt Application & Signals
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)

        self.bridge = AppBridge()
        self.bridge.signal_open_dashboard.connect(self._open_settings)

        # Initialize History Manager
        self.history_mgr = HistoryManager(max_items=self.config.max_history_items)

        # Initialize UI Components
        self.overlay = RecordingOverlay()
        self.settings_window = SettingsWindow(
            self.config,
            on_save_callback=self._on_config_updated,
            on_reinject_callback=self._on_reinject_requested
        )

        # Create System Tray
        self.tray = QSystemTrayIcon(QIcon(create_tray_icon_pixmap()), self.qt_app)
        self.tray.setToolTip("VoxType - Local AI Voice Dictation Engine")
        self._build_tray_menu()
        self.tray.show()

        # Initialize Core Engines & Utilities
        self.audio = AudioRecorder(
            device_index=self.config.audio_device_index,
            gain=self.config.whisper_mode_gain
        )
        self.audio_muter = AudioMuter(enabled=self.config.mute_pc_audio)

        self.asr = ASREngine(
            model_name=self.config.whisper_model,
            compute_type=self.config.whisper_compute_type,
            device=self.config.whisper_device,
            language=self.config.whisper_language,
            translate_mode=self.config.translate_mode
        )
        self.asr.set_dictionary(self.config.custom_terms)

        self.llm = LLMEngine(
            model=self.config.ollama_model,
            system_prompt=self.config.system_prompt,
            command_prompt=self.config.command_mode_prompt,
            temperature=self.config.llm_temperature
        )

        self.injector = TextInjector(
            paste_delay_ms=0,
            restore_clipboard=self.config.restore_clipboard
        )

        # State tracking for Command Mode, Pre-processing, & VRAM Offload
        self.current_selection = ""
        self.latest_stream_transcript = ""
        self._last_activity_time = time.time()

        # Initialize Global Hotkeys
        self.hotkeys = HotkeyManager(
            on_recording_start=self._on_recording_start,
            on_recording_stop=self._on_recording_stop,
            on_toggle_dashboard=self._open_settings,
            double_tap_ms=self.config.double_tap_ms
        )

        # Start background IPC server & VRAM idle monitor
        threading.Thread(target=self._start_ipc_server, daemon=True).start()
        threading.Thread(target=self._vram_idle_monitor, daemon=True).start()

    def _start_ipc_server(self):
        """Listen for incoming IPC activation signals from duplicate launches."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("127.0.0.1", IPC_PORT))
            server.listen(5)
            print(f"[IPC] Listening for dashboard activation signals on port {IPC_PORT}...")
            while True:
                conn, _ = server.accept()
                data = conn.recv(1024)
                if b"OPEN_DASHBOARD" in data:
                    self.bridge.signal_open_dashboard.emit()
                conn.close()
        except Exception as e:
            print(f"[IPC] Server error: {e}")

    def _build_tray_menu(self):
        menu = QMenu()

        status_action = menu.addAction("VoxType Dashboard (Ctrl+Win+S)")
        status_action.triggered.connect(self._open_settings)
        menu.addSeparator()

        settings_action = menu.addAction("⚙️ Open Settings Dashboard...")
        settings_action.triggered.connect(self._open_settings)

        menu.addSeparator()
        quit_action = menu.addAction("Quit VoxType")
        quit_action.triggered.connect(self._quit_app)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_icon_activated)

    def _on_tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._open_settings()

    def _open_settings(self):
        self.settings_window._refresh_history_table()
        self.settings_window.show()
        self.settings_window.setWindowState(self.settings_window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.settings_window.activateWindow()
        self.settings_window.raise_()

    def _on_reinject_requested(self, text: str):
        print(f"[VoxType] Re-injecting selected history text ({len(text)} chars)...")
        if self.config.append_trailing_space and not text.endswith(" ") and not text.endswith("\n"):
            text += " "
        self.injector.inject(text)

    def _vram_idle_monitor(self):
        """Monitor idle time and unload Whisper model from GPU VRAM when threshold is reached."""
        while True:
            time.sleep(10)
            mins = self.config.vram_offload_mins
            if mins > 0 and self.asr.is_loaded:
                idle_sec = time.time() - self._last_activity_time
                if idle_sec >= (mins * 60):
                    print(f"[VRAM Monitor] Idle for {int(idle_sec)}s (>{mins}m). Unloading Whisper from GPU VRAM.")
                    self.asr.unload_model()

    def _on_config_updated(self, new_config: VoxTypeConfig):
        print("[VoxType] Applying updated configuration...")
        self.config = new_config

        # Update Audio Recorder (device & gain)
        self.audio.device_index = self.config.audio_device_index
        self.audio.gain = self.config.whisper_mode_gain
        self.audio_muter.enabled = self.config.mute_pc_audio

        # Update ASR
        self.asr.set_dictionary(self.config.custom_terms)
        self.asr.language = self.config.whisper_language
        self.asr.translate_mode = self.config.translate_mode
        if self.asr.model_name != self.config.whisper_model or self.asr.compute_type != self.config.whisper_compute_type:
            self.asr.model_name = self.config.whisper_model
            self.asr.compute_type = self.config.whisper_compute_type
            self.asr._load_model()

        # Update LLM
        self.llm.update_model(self.config.ollama_model)
        self.llm.update_prompts(self.config.system_prompt, self.config.command_mode_prompt)
        self.llm.temperature = self.config.llm_temperature

        # Update Injector
        self.injector.paste_delay_sec = 0.0
        self.injector.restore_clipboard = self.config.restore_clipboard

        # Update Hotkeys
        self.hotkeys.double_tap_sec = self.config.double_tap_ms / 1000.0

    def _on_recording_start(self, is_command_mode: bool = False):
        self._last_activity_time = time.time()
        self.latest_stream_transcript = ""
        self.audio_muter.mute()

        if self.config.play_sounds:
            play_sound("start.wav")

        if self.config.show_overlay:
            self.overlay.safe_show()

        if is_command_mode:
            self.current_selection = self.injector.capture_selection()

        self.audio.start()

        # Start silent live background pre-processor thread
        threading.Thread(
            target=self._stream_preprocessor_loop,
            daemon=True
        ).start()

    def _stream_preprocessor_loop(self):
        """Silently pre-transcribe live audio snapshots in background on GPU while user speaks."""
        while self.audio.is_recording:
            time.sleep(0.4)
            if not self.audio.is_recording:
                break
            snapshot = self.audio.get_current_snapshot()
            if len(snapshot) >= 16000:
                try:
                    partial = self.asr.transcribe(snapshot, verbose=False)
                    if partial:
                        self.latest_stream_transcript = partial
                except Exception:
                    pass

    def _on_recording_stop(self, is_command_mode: bool = False):
        self._last_activity_time = time.time()
        audio_data = self.audio.stop()

        if self.config.show_overlay:
            self.overlay.safe_hide()

        if self.config.play_sounds:
            play_sound("stop.wav")

        selection = self.current_selection
        self.current_selection = ""

        # Launch pipeline IMMEDIATELY
        threading.Thread(
            target=self._process_audio_pipeline,
            args=(audio_data, is_command_mode, selection),
            daemon=True
        ).start()

        # Restore audio in parallel background thread so COM calls never delay injection
        threading.Thread(
            target=self.audio_muter.unmute,
            daemon=True
        ).start()

    def _process_audio_pipeline(self, audio_data, is_command_mode: bool, selection: str):
        if len(audio_data) == 0:
            return

        # 1. Transcribe with Whisper ASR
        raw_text = self.asr.transcribe(audio_data, verbose=True)
        if not raw_text.strip():
            raw_text = self.latest_stream_transcript

        if not raw_text.strip():
            return

        mode_label = "Dictation"
        # 2. Process with LLM (or passthrough if LLM cleanup is disabled)
        if is_command_mode and selection:
            mode_label = "Command Mode"
            output_text = self.llm.command(selection, raw_text)
        elif self.config.use_llm_cleanup:
            mode_label = "AI Cleanup"
            output_text = self.llm.cleanup(raw_text)
        else:
            output_text = raw_text

        # 3. Record in persistent history
        self.history_mgr.add_entry(
            text=output_text,
            mode=mode_label,
            language=self.config.whisper_language or "auto"
        )

        # 4. Inject text instantly at current cursor location
        if output_text.strip():
            if self.config.append_trailing_space and not output_text.endswith(" ") and not output_text.endswith("\n"):
                output_text += " "
            self.injector.inject(output_text)

    def run(self):
        print("[VoxType] Ready. Press Ctrl+Win to dictate, or Ctrl+Win+S for Dashboard!")
        self.hotkeys.start()
        self._open_settings()
        sys.exit(self.qt_app.exec())

    def _quit_app(self):
        print("[VoxType] Shutting down...")
        self.hotkeys.stop()
        self.tray.hide()
        self.qt_app.quit()

def main():
    if check_single_instance_or_trigger_dashboard():
        sys.exit(0)
    app = VoxTypeApp()
    app.run()

if __name__ == "__main__":
    main()
