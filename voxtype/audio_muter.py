from pycaw.pycaw import AudioUtilities

class AudioMuter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._was_muted: bool = False

    def mute(self) -> None:
        if not self.enabled:
            return
        try:
            device = AudioUtilities.GetSpeakers()
            volume = device.EndpointVolume
            self._was_muted = bool(volume.GetMute())
            volume.SetMute(True, None)
            print("[AudioMuter] Muted PC background audio.")
        except Exception as e:
            print(f"[AudioMuter] Error muting PC audio: {e}")

    def unmute(self) -> None:
        if not self.enabled:
            return
        try:
            device = AudioUtilities.GetSpeakers()
            volume = device.EndpointVolume
            volume.SetMute(self._was_muted, None)
            print(f"[AudioMuter] Restored PC background audio (muted={self._was_muted}).")
        except Exception as e:
            print(f"[AudioMuter] Error restoring PC audio: {e}")
