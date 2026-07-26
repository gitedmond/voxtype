import os
import sys
import time
import ctypes
import pyperclip
from pynput.keyboard import Controller, Key

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12   # Alt
VK_LWIN = 0x5B
VK_RWIN = 0x5C
KEYEVENTF_KEYUP = 0x0002

class TextInjector:
    def __init__(self, paste_delay_ms: int = 0, restore_clipboard: bool = False):
        self._pynput_controller = Controller()
        self.paste_delay_sec = max(0.0, paste_delay_ms / 1000.0)
        self.restore_clipboard = restore_clipboard

    def _release_all_modifiers(self) -> None:
        """Force release all modifier keys on Windows so Win/Ctrl/Shift state is clean."""
        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            for vk in (VK_CONTROL, VK_SHIFT, VK_MENU, VK_LWIN, VK_RWIN):
                user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    def inject(self, text: str) -> None:
        """Inject text instantly into the active app via Windows clipboard paste."""
        if not text:
            return

        print(f"[Injector] Injecting {len(text)} characters instantly...")

        original = ""
        if self.restore_clipboard:
            try:
                original = pyperclip.paste()
            except Exception:
                original = ""

        # Copy text to clipboard instantly
        pyperclip.copy(text)
        if self.paste_delay_sec > 0:
            time.sleep(self.paste_delay_sec)

        # Native Ctrl+V press & release
        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            # Quick modifier release
            for vk in (VK_CONTROL, VK_SHIFT, VK_MENU, VK_LWIN, VK_RWIN):
                user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(0x56, 0, 0, 0)  # 0x56 = 'V' key
            user32.keybd_event(0x56, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        else:
            self._pynput_controller.press(Key.ctrl)
            self._pynput_controller.press('v')
            self._pynput_controller.release('v')
            self._pynput_controller.release(Key.ctrl)

        # Optional clipboard restoration (disabled by default)
        if self.restore_clipboard and original:
            time.sleep(0.5)
            try:
                pyperclip.copy(original)
            except Exception:
                pass

    def capture_selection(self) -> str:
        """Capture currently selected text via Ctrl+C simulation."""
        try:
            original = pyperclip.paste()
        except Exception:
            original = ""

        self._release_all_modifiers()

        pyperclip.copy("__VOXTYPE_SEL_MARKER__")

        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(0x43, 0, 0, 0)  # 0x43 = 'C' key
            user32.keybd_event(0x43, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        else:
            self._pynput_controller.press(Key.ctrl)
            self._pynput_controller.press('c')
            self._pynput_controller.release('c')
            self._pynput_controller.release(Key.ctrl)

        time.sleep(0.08)
        selected = pyperclip.paste()

        if selected == "__VOXTYPE_SEL_MARKER__":
            pyperclip.copy(original)
            return ""

        return selected
