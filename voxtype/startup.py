import os
import sys
import winreg

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "VoxType"

def get_launch_command() -> str:
    """Get windowless launch command for VoxType."""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pythonw_path = os.path.join(project_dir, ".venv", "Scripts", "pythonw.exe")
    if os.path.exists(pythonw_path):
        return f'"{pythonw_path}" -m voxtype.app'
    run_bat = os.path.join(project_dir, "run.bat")
    return f'"{run_bat}"'

def set_run_on_startup(enable: bool) -> bool:
    """Add or remove Windows Registry run key."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            cmd = get_launch_command()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            print(f"[Startup] Added registry key: {APP_NAME} -> {cmd}")
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
                print(f"[Startup] Removed registry key: {APP_NAME}")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[Startup] Error updating startup registry: {e}")
        return False

def is_run_on_startup_enabled() -> bool:
    """Check if Windows Registry run key exists."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(value)
    except FileNotFoundError:
        return False
