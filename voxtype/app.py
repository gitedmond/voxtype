import sys
import time
import threading
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt

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

        # Initialize Qt Application
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)

        # Initialize UI Components
        self.overlay = RecordingOverlay()
        self.settings_window = SettingsWindow(self.config, on_save_callback=self._on_config_updated)

        # Create System Tray
        self.tray = QSystemTrayIcon(QIcon(create_tray_icon_pixmap()), self.qt_app)
        self.tray.setToolTip("VoxType - Local AI Voice Dictation Engine")
        self._build_tray_menu()
        self.tray.show()

        # Initialize Core Engines & Utilities
        self.audio = AudioRecorder()
        self.audio_muter = AudioMuter(enabled=self.config.mute_pc_audio)

        self.asr = ASREngine(
            model_name=self.config.whisper_model,
            compute_type=self.config.whisper_compute_type,
            device=self.config.whisper_device,
            language=self.config.whisper_language
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

        # State tracking for Command Mode & Pre-processing
        self.current_selection = ""
        self.latest_stream_transcript = ""

        # Initialize Global Hotkeys
        self.hotkeys = HotkeyManager(
            on_recording_start=self._on_recording_start,
            on_recording_stop=self._on_recording_stop,
            double_tap_ms=self.config.double_tap_ms
        )

    def _build_tray_menu(self):
        menu = QMenu()

        status_action = menu.addAction("VoxType Dashboard (Ctrl+Win)")
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
        self.settings_window.show()
        self.settings_window.activateWindow()

    def _on_config_updated(self, new_config: VoxTypeConfig):
        print("[VoxType] Applying updated configuration...")
        self.config = new_config

        # Update Audio Muter
        self.audio_muter.enabled = self.config.mute_pc_audio

        # Update ASR
        self.asr.set_dictionary(self.config.custom_terms)
        self.asr.language = self.config.whisper_language
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

        # 2. Process with LLM (or passthrough if LLM cleanup is disabled)
        if is_command_mode and selection:
            output_text = self.llm.command(selection, raw_text)
        elif self.config.use_llm_cleanup:
            output_text = self.llm.cleanup(raw_text)
        else:
            output_text = raw_text

        # 3. Inject text instantly at current cursor location
        if output_text.strip():
            if self.config.append_trailing_space and not output_text.endswith(" ") and not output_text.endswith("\n"):
                output_text += " "
            self.injector.inject(output_text)

    def run(self):
        print("[VoxType] Ready. Press Ctrl+Win to dictate!")
        self.hotkeys.start()
        self._open_settings()
        sys.exit(self.qt_app.exec())

    def _quit_app(self):
        print("[VoxType] Shutting down...")
        self.hotkeys.stop()
        self.tray.hide()
        self.qt_app.quit()

def main():
    app = VoxTypeApp()
    app.run()

if __name__ == "__main__":
    main()
