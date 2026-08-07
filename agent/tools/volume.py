"""
volume.py — Control system volume on Windows using pycaw.
"""

from langchain_core.tools import tool

from agent.tools.safety import logger


def _get_volume_interface():
    """Get the Windows audio endpoint volume interface."""
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


@tool
def get_volume() -> str:
    """
    Get the current system volume level (0-100) and mute status.
    """
    try:
        volume = _get_volume_interface()
        current = volume.GetMasterVolumeLevelScalar()
        muted = volume.GetMute()
        level = int(current * 100)
        mute_str = " (🔇 MUTED)" if muted else ""
        result = f"🔊 Volume: {level}%{mute_str}"
        logger.log("get_volume", {}, result)
        return result
    except Exception as e:
        msg = f"❌ Failed to get volume: {e}"
        logger.log("get_volume", {}, msg, status="error")
        return msg


@tool
def set_volume(level: int) -> str:
    """
    Set the system volume to a specific level.

    Args:
        level: Volume level from 0 (silent) to 100 (max)
    """
    try:
        level = max(0, min(100, level))
        volume = _get_volume_interface()
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        logger.log("set_volume", {"level": level}, f"Volume set to {level}%")
        return f"✅ Volume set to {level}%"
    except Exception as e:
        msg = f"❌ Failed to set volume: {e}"
        logger.log("set_volume", {"level": level}, msg, status="error")
        return msg


@tool
def toggle_mute() -> str:
    """
    Toggle the system mute on/off.
    """
    try:
        volume = _get_volume_interface()
        current_mute = volume.GetMute()
        volume.SetMute(not current_mute, None)
        new_state = "🔇 Muted" if not current_mute else "🔊 Unmuted"
        logger.log("toggle_mute", {}, new_state)
        return f"✅ {new_state}"
    except Exception as e:
        msg = f"❌ Failed to toggle mute: {e}"
        logger.log("toggle_mute", {}, msg, status="error")
        return msg
