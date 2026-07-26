import time
import threading
from enum import Enum, auto
from pynput import keyboard

class HotkeyState(Enum):
    IDLE = auto()
    RECORDING_HOLD = auto()
    WAITING_DOUBLE_TAP = auto()
    RECORDING_LOCKED = auto()

class HotkeyManager:
    def __init__(self, on_recording_start, on_recording_stop, on_toggle_dashboard=None, double_tap_ms: int = 400):
        """
        on_recording_start: callable(is_command_mode: bool)
        on_recording_stop: callable(is_command_mode: bool)
        on_toggle_dashboard: callable()
        """
        self.on_recording_start = on_recording_start
        self.on_recording_stop = on_recording_stop
        self.on_toggle_dashboard = on_toggle_dashboard
        self.double_tap_sec = double_tap_ms / 1000.0

        self.state = HotkeyState.IDLE
        self._ctrl_pressed = False
        self._win_pressed = False
        self._shift_pressed = False

        self._press_time = 0.0
        self._last_quick_release_time = 0.0
        self._timer: threading.Timer | None = None
        self._is_command_mode = False
        self._lock = threading.Lock()
        self._listener: keyboard.Listener | None = None
        self._kb_controller = keyboard.Controller()

    def start(self) -> None:
        print("[Hotkeys] Starting global hotkey listener (Ctrl+Win dictation, Ctrl+Win+S dashboard)...")
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _is_hotkey_combo(self) -> bool:
        return self._ctrl_pressed and self._win_pressed

    def _prevent_start_menu(self) -> None:
        """Prevent Windows Start Menu from popping up when Win key is released."""
        try:
            self._kb_controller.press(keyboard.Key.shift)
            self._kb_controller.release(keyboard.Key.shift)
        except Exception:
            pass

    def _on_press(self, key) -> None:
        # Update key states
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.ctrl):
            self._ctrl_pressed = True
        elif key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            self._win_pressed = True
        elif key in (keyboard.Key.shift, keyboard.Key.shift_r, keyboard.Key.shift_l):
            self._shift_pressed = True

        with self._lock:
            # Check for Ctrl+Win+S (Toggle Dashboard)
            if self._is_hotkey_combo() and hasattr(key, 'char') and key.char in ('s', 'S'):
                self._prevent_start_menu()
                if self.on_toggle_dashboard:
                    print("[Hotkeys] Ctrl+Win+S pressed -> Opening Dashboard.")
                    self.on_toggle_dashboard()
                    return

            if self._is_hotkey_combo():
                self._prevent_start_menu()
                now = time.time()

                if self.state == HotkeyState.RECORDING_LOCKED:
                    # Tap while locked -> stop recording
                    print("[Hotkeys] Stopping locked recording.")
                    self.state = HotkeyState.IDLE
                    cmd_mode = self._is_command_mode
                    self._is_command_mode = False
                    self.on_recording_stop(cmd_mode)
                    return

                if self.state == HotkeyState.IDLE or self.state == HotkeyState.WAITING_DOUBLE_TAP:
                    if self.state == HotkeyState.WAITING_DOUBLE_TAP:
                        # Cancel double tap timeout timer
                        if self._timer:
                            self._timer.cancel()
                            self._timer = None

                        if (now - self._last_quick_release_time) <= self.double_tap_sec:
                            # 2nd tap detected within time limit! Lock recording.
                            print("[Hotkeys] Double tap detected -> Locking recording ON.")
                            self.state = HotkeyState.RECORDING_LOCKED
                            return

                    # Normal start
                    self._press_time = now
                    self._is_command_mode = self._shift_pressed
                    self.state = HotkeyState.RECORDING_HOLD
                    print(f"[Hotkeys] Hotkey pressed -> Starting recording (Command Mode: {self._is_command_mode})")
                    self.on_recording_start(self._is_command_mode)

    def _on_release(self, key) -> None:
        was_combo = self._is_hotkey_combo()

        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.ctrl):
            self._ctrl_pressed = False
        elif key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            self._win_pressed = False
        elif key in (keyboard.Key.shift, keyboard.Key.shift_r, keyboard.Key.shift_l):
            self._shift_pressed = False

        with self._lock:
            if was_combo and not self._is_hotkey_combo():
                now = time.time()
                if self.state == HotkeyState.RECORDING_HOLD:
                    duration = now - self._press_time
                    if duration < self.double_tap_sec:
                        # Quick tap release: wait to see if a second tap follows
                        self.state = HotkeyState.WAITING_DOUBLE_TAP
                        self._last_quick_release_time = now

                        # Start timer to stop if no 2nd tap occurs
                        self._timer = threading.Timer(
                            self.double_tap_sec,
                            self._handle_single_tap_timeout,
                            args=(self._is_command_mode,)
                        )
                        self._timer.daemon = True
                        self._timer.start()
                    else:
                        # Long hold release (Hold-to-Talk) -> stop recording
                        print(f"[Hotkeys] Hold-to-Talk released ({duration:.2f}s) -> Stopping recording.")
                        self.state = HotkeyState.IDLE
                        cmd_mode = self._is_command_mode
                        self._is_command_mode = False
                        self.on_recording_stop(cmd_mode)

    def _handle_single_tap_timeout(self, cmd_mode: bool) -> None:
        with self._lock:
            if self.state == HotkeyState.WAITING_DOUBLE_TAP:
                print("[Hotkeys] Single tap timeout -> Stopping recording.")
                self.state = HotkeyState.IDLE
                self._is_command_mode = False
                self.on_recording_stop(cmd_mode)
