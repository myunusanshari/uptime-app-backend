"""
Utility functions for sound handling
"""
import os

def normalize_sound_name(sound_name: str | None) -> str:
    """
    Normalize sound name by removing file extension.
    Android res/raw files are referenced without extension.
    
    Args:
        sound_name: Sound filename (may include extension)
        
    Returns:
        Sound name without extension
        
    Examples:
        "alarm.wav" -> "alarm"
        "beep1.mp3" -> "beep1"
        "default_down" -> "default_down"
    """
    if not sound_name:
        return "default_down"
    
    # Remove file extension if present
    name_without_ext = os.path.splitext(sound_name)[0]
    
    return name_without_ext if name_without_ext else "default_down"
