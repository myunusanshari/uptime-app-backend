from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
from pathlib import Path
import shutil
from typing import List

router = APIRouter()

# Directory to store custom sound files
SOUNDS_DIR = Path(__file__).parent.parent.parent / "custom_sounds"
SOUNDS_DIR.mkdir(exist_ok=True)

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/upload")
async def upload_sound(file: UploadFile = File(...)):
    """
    Upload a custom notification sound file.
    
    Args:
        file: Audio file (mp3, wav, m4a, aac, ogg) - max 5MB
        
    Returns:
        Dict with filename and message
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: 5MB"
        )
    
    # Sanitize filename
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ('_', '-', '.'))
    file_path = SOUNDS_DIR / safe_filename
    
    # Check if file already exists
    if file_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"File '{safe_filename}' already exists. Please rename or delete the existing file first."
        )
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "filename": safe_filename,
            "message": "Sound file uploaded successfully"
        }
    except Exception as e:
        # Clean up partial file if error occurs
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")


@router.get("/list")
async def list_sounds():
    """
    Get list of all available notification sounds (built-in + custom).
    
    Returns:
        Dict with built_in and custom sound lists
    """
    # Built-in sounds (these are in the Android app's res/raw folder)
    built_in_sounds = [
        {"name": "default_down", "display_name": "Default Down Alert", "type": "built-in"},
        {"name": "default_up", "display_name": "Default Up Alert", "type": "built-in"},
        {"name": "beep1", "display_name": "Beep 1", "type": "built-in"},
        {"name": "beep2", "display_name": "Beep 2", "type": "built-in"},
    ]
    
    # Custom uploaded sounds
    custom_sounds = []
    if SOUNDS_DIR.exists():
        for sound_file in SOUNDS_DIR.iterdir():
            if sound_file.is_file() and sound_file.suffix.lower() in ALLOWED_EXTENSIONS:
                custom_sounds.append({
                    "name": sound_file.stem,  # Filename without extension
                    "display_name": sound_file.name,
                    "type": "custom",
                    "size": sound_file.stat().st_size,
                    "extension": sound_file.suffix
                })
    
    return {
        "built_in": built_in_sounds,
        "custom": custom_sounds,
        "total": len(built_in_sounds) + len(custom_sounds)
    }


@router.delete("/{filename}")
async def delete_sound(filename: str):
    """
    Delete a custom sound file.
    
    Args:
        filename: Name of the file to delete (with extension)
        
    Returns:
        Success message
    """
    file_path = SOUNDS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Sound file not found")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    try:
        file_path.unlink()
        return {"success": True, "message": f"Sound file '{filename}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@router.get("/download/{filename}")
async def download_sound(filename: str):
    """
    Download a custom sound file.
    
    Args:
        filename: Name of the file to download
        
    Returns:
        File response
    """
    file_path = SOUNDS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Sound file not found")
    
    return FileResponse(
        path=file_path,
        media_type='application/octet-stream',
        filename=filename
    )
