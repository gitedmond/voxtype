import os
import sys
import ollama
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QComboBox, QSlider, QCheckBox, QPlainTextEdit, QPushButton,
    QListWidget, QInputDialog, QMessageBox, QFileDialog, QGroupBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from voxtype.config import VoxTypeConfig, save_config
from voxtype.startup import set_run_on_startup, is_run_on_startup_enabled

OLLAMA_WHITE_MINIMAL_STYLESHEET = """
QMainWindow {
    background-color: #FFFFFF;
}
QWidget {
    color: #0F172A;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background-color: #FFFFFF;
    padding: 16px;
}
QTabBar::tab {
    background-color: #F8FAFC;
    color: #64748B;
    border: 1px solid #E2E8F0;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #0F172A;
    border-bottom: 2px solid #0F172A;
}
QTabBar::tab:hover {
    color: #0F172A;
    background-color: #F1F5F9;
}
QGroupBox {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #0F172A;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QComboBox, QLineEdit, QPlainTextEdit, QSpinBox {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 12px;
    color: #0F172A;
}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #0F172A;
    background-color: #FFFFFF;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QPushButton {
    background-color: #0F172A;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #334155;
}
QPushButton:pressed {
    background-color: #000000;
}
QPushButton#secondaryBtn {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    color: #334155;
}
QPushButton#secondaryBtn:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}
QListWidget {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #0F172A;
    color: white;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #CBD5E1;
    background-color: #F8FAFC;
}
QCheckBox::indicator:checked {
    background-color: #0F172A;
    border: 1px solid #0F172A;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #E2E8F0;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #0F172A;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #0F172A;
    width: 16px;
    height: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}
"""

class SettingsWindow(QMainWindow):
    def __init__(self, config: VoxTypeConfig, on_save_callback):
        super().__init__()
        self.config = config
        self.on_save_callback = on_save_callback

        self.setWindowTitle("VoxType Settings")
        self.resize(680, 600)
        self.setStyleSheet(OLLAMA_WHITE_MINIMAL_STYLESHEET)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Minimal Header
        self._build_header_bar(layout)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_general_tab()
        self._build_speech_tab()
        self._build_cleanup_tab()
        self._build_dictionary_tab()
        self._build_audio_visual_tab()
        self._build_about_tab()

        # Footer
        btn_layout = QHBoxLayout()
        status_info = QLabel("VoxType v1.0 • Local AI Dictation")
        status_info.setStyleSheet("color: #94A3B8; font-size: 12px;")
        btn_layout.addWidget(status_info)
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryBtn")
        self.cancel_btn.clicked.connect(self.hide)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("padding: 8px 24px;")
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)
        self.setCentralWidget(main_widget)

    def _build_header_bar(self, parent_layout):
        header = QHBoxLayout()

        title_box = QVBoxLayout()
        app_title = QLabel("VoxType")
        app_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px;")
        sub_title = QLabel("Minimalist Local Voice Dictation Engine")
        sub_title.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(app_title)
        title_box.addWidget(sub_title)
        header.addLayout(title_box)

        header.addStretch()

        status_badge = QLabel("  ● Ready (Ctrl+Win)  ")
        status_badge.setStyleSheet(
            "background-color: #F1F5F9; color: #0F172A; font-weight: 600; "
            "border: 1px solid #E2E8F0; border-radius: 12px; padding: 6px 12px; font-size: 12px;"
        )
        header.addWidget(status_badge)

        parent_layout.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #E2E8F0; border: none; min-height: 1px;")
        parent_layout.addWidget(line)

    def _build_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("System & Launch Options")
        form = QFormLayout(box)

        self.startup_check = QCheckBox("Launch VoxType automatically on Windows Startup")
        self.startup_check.setChecked(is_run_on_startup_enabled())
        form.addRow("Windows Startup:", self.startup_check)

        self.space_check = QCheckBox("Automatically append a space after each dictated sentence")
        self.space_check.setChecked(self.config.append_trailing_space)
        form.addRow("Sentence Format:", self.space_check)

        self.hotkey_label = QLabel("Ctrl + Win (Cmd)")
        self.hotkey_label.setStyleSheet("color: #0F172A; font-weight: bold;")
        form.addRow("Dictation Hotkey:", self.hotkey_label)

        self.cmd_hotkey_label = QLabel("Ctrl + Win + Shift")
        self.cmd_hotkey_label.setStyleSheet("color: #0F172A; font-weight: bold;")
        form.addRow("Command Mode Hotkey:", self.cmd_hotkey_label)

        # Double tap slider
        self.double_tap_slider = QSlider(Qt.Orientation.Horizontal)
        self.double_tap_slider.setRange(200, 800)
        self.double_tap_slider.setValue(self.config.double_tap_ms)
        self.double_tap_val_label = QLabel(f"{self.config.double_tap_ms} ms")
        self.double_tap_val_label.setStyleSheet("color: #0F172A; font-weight: bold;")
        self.double_tap_slider.valueChanged.connect(
            lambda v: self.double_tap_val_label.setText(f"{v} ms")
        )

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.double_tap_slider)
        slider_layout.addWidget(self.double_tap_val_label)
        form.addRow("Double-Tap Lock Delay:", slider_layout)

        layout.addWidget(box)
        layout.addStretch()
        self.tabs.addTab(tab, "General")

    def _build_speech_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("Whisper ASR Engine Settings")
        form = QFormLayout(box)

        self.whisper_model_combo = QComboBox()
        models = ["large-v3-turbo", "large-v3", "medium", "small", "base", "tiny"]
        self.whisper_model_combo.addItems(models)
        self.whisper_model_combo.setCurrentText(self.config.whisper_model)
        form.addRow("Whisper Model:", self.whisper_model_combo)

        self.compute_type_combo = QComboBox()
        self.compute_type_combo.addItems(["int8", "float16", "float32"])
        self.compute_type_combo.setCurrentText(self.config.whisper_compute_type)
        form.addRow("Compute Precision:", self.compute_type_combo)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["Auto-Detect", "en", "es", "fr", "de", "it", "zh", "ja", "hi"])
        if self.config.whisper_language is None:
            self.language_combo.setCurrentText("Auto-Detect")
        else:
            self.language_combo.setCurrentText(self.config.whisper_language)
        form.addRow("Speech Language:", self.language_combo)

        layout.addWidget(box)

        info = QLabel("Default: large-v3-turbo on INT8 for ultra-fast GPU dictation.")
        info.setStyleSheet("color: #64748B; font-size: 12px; margin-top: 8px;")
        layout.addWidget(info)

        layout.addStretch()
        self.tabs.addTab(tab, "Speech ASR")

    def _build_cleanup_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("LLM Dictation Cleanup & Command Mode")
        box_layout = QVBoxLayout(box)

        self.use_llm_check = QCheckBox("Enable LLM Cleanup for Dictation (Uncheck for instant Raw Dictation)")
        self.use_llm_check.setChecked(self.config.use_llm_cleanup)
        box_layout.addWidget(self.use_llm_check)

        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Ollama Model:"))
        self.ollama_model_combo = QComboBox()
        model_layout.addWidget(self.ollama_model_combo, 1)

        refresh_btn = QPushButton("Refresh Models")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.clicked.connect(self._refresh_ollama_models)
        model_layout.addWidget(refresh_btn)
        box_layout.addLayout(model_layout)

        layout.addWidget(box)

        # Prompts
        layout.addWidget(QLabel("Dictation System Prompt:"))
        self.sys_prompt_edit = QPlainTextEdit()
        self.sys_prompt_edit.setPlainText(self.config.system_prompt)
        layout.addWidget(self.sys_prompt_edit)

        layout.addWidget(QLabel("Command Mode System Prompt:"))
        self.cmd_prompt_edit = QPlainTextEdit()
        self.cmd_prompt_edit.setPlainText(self.config.command_mode_prompt)
        layout.addWidget(self.cmd_prompt_edit)

        self.tabs.addTab(tab, "AI Cleanup (LLM)")
        self._refresh_ollama_models()

    def _refresh_ollama_models(self):
        self.ollama_model_combo.clear()
        try:
            res = ollama.list()
            models = [m.model for m in res.models]
            self.ollama_model_combo.addItems(models)
            if self.config.ollama_model in models:
                self.ollama_model_combo.setCurrentText(self.config.ollama_model)
        except Exception as e:
            print(f"[Settings] Error listing Ollama models: {e}")
            self.ollama_model_combo.addItem(self.config.ollama_model)

    def _build_dictionary_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Personal Dictionary (Custom jargon & proper nouns injected into Whisper ASR):"))
        self.dict_list = QListWidget()
        self.dict_list.addItems(self.config.custom_terms)
        layout.addWidget(self.dict_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Word")
        add_btn.clicked.connect(self._add_dict_word)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("secondaryBtn")
        remove_btn.clicked.connect(self._remove_dict_word)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "Personal Dictionary")

    def _add_dict_word(self):
        word, ok = QInputDialog.getText(self, "Add Word", "Enter term/jargon name:")
        if ok and word.strip():
            self.dict_list.addItem(word.strip())

    def _remove_dict_word(self):
        for item in self.dict_list.selectedItems():
            self.dict_list.takeItem(self.dict_list.row(item))

    def _build_audio_visual_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("Audio & Hardware Controls")
        box_layout = QVBoxLayout(box)

        self.mute_pc_check = QCheckBox("Mute PC Background Audio While Dictating (Prevents speaker audio from entering mic)")
        self.mute_pc_check.setChecked(self.config.mute_pc_audio)
        box_layout.addWidget(self.mute_pc_check)

        self.sound_check = QCheckBox("Enable Audio Feedback Beeps (Start / Stop cues)")
        self.sound_check.setChecked(self.config.play_sounds)
        box_layout.addWidget(self.sound_check)

        self.overlay_check = QCheckBox("Enable Recording Floating Indicator (Pulsing Red Dot)")
        self.overlay_check.setChecked(self.config.show_overlay)
        box_layout.addWidget(self.overlay_check)

        layout.addWidget(box)
        layout.addStretch()
        self.tabs.addTab(tab, "Audio & Visual")

    def _build_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("Hardware & System Diagnostics")
        form = QFormLayout(box)

        form.addRow("Application:", QLabel("VoxType v1.0.0 (Local AI Dictation)"))
        form.addRow("GPU Hardware:", QLabel("NVIDIA GeForce RTX 5070 Ti (16GB VRAM)"))
        form.addRow("ASR Engine:", QLabel("faster-whisper (Large-v3-Turbo, CUDA INT8)"))
        form.addRow("LLM Engine:", QLabel("Ollama (llama3.2:3b / llama3.1:8b)"))
        form.addRow("Audio Control:", QLabel("PyCAW Master Volume Controller"))

        layout.addWidget(box)
        layout.addStretch()

        self.tabs.addTab(tab, "Diagnostics")

    def _save_settings(self):
        run_startup = self.startup_check.isChecked()
        set_run_on_startup(run_startup)
        self.config.run_on_startup = run_startup

        self.config.double_tap_ms = self.double_tap_slider.value()
        self.config.append_trailing_space = self.space_check.isChecked()
        self.config.whisper_model = self.whisper_model_combo.currentText()
        self.config.whisper_compute_type = self.compute_type_combo.currentText()

        lang = self.language_combo.currentText()
        self.config.whisper_language = None if lang == "Auto-Detect" else lang

        self.config.use_llm_cleanup = self.use_llm_check.isChecked()

        if self.ollama_model_combo.currentText():
            self.config.ollama_model = self.ollama_model_combo.currentText()

        self.config.system_prompt = self.sys_prompt_edit.toPlainText()
        self.config.command_mode_prompt = self.cmd_prompt_edit.toPlainText()

        terms = [self.dict_list.item(i).text() for i in range(self.dict_list.count())]
        self.config.custom_terms = terms

        self.config.mute_pc_audio = self.mute_pc_check.isChecked()
        self.config.play_sounds = self.sound_check.isChecked()
        self.config.show_overlay = self.overlay_check.isChecked()

        save_config(self.config)
        QMessageBox.information(self, "Saved", "VoxType settings saved successfully!")
        if self.on_save_callback:
            self.on_save_callback(self.config)
        self.hide()
