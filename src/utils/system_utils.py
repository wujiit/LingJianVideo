import os
import sys

def find_ffmpeg_executable() -> str:
    """
    Find FFmpeg executable in common locations.
    Returns the path to the executable if found, otherwise returns 'ffmpeg' (assuming it's in PATH).
    """
    # Check common locations without running them
    base_path = os.path.dirname(os.path.abspath(__file__)) # src/utils
    
    # Adjust base path to point to root or app dir
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        base_path = os.path.dirname(sys.executable)
    else:
        # Running from source (src/utils -> src -> root)
        # Go up two levels to get to project root
        base_path = os.path.abspath(os.path.join(base_path, '..', '..'))
        
    possible_paths = [
        'ffmpeg.exe',
        os.path.join(base_path, 'ffmpeg.exe'),
        os.path.join(base_path, 'bin', 'ffmpeg.exe'),
        os.path.join(base_path, '_internal', 'bin', 'ffmpeg.exe'),
        os.path.join(base_path, 'ffmpeg', 'bin', 'ffmpeg.exe'),
        # Add these for development environment compatibility
        os.path.join(base_path, 'resources', 'bin', 'ffmpeg', 'ffmpeg.exe'),
        os.path.join(base_path, '..', 'resources', 'bin', 'ffmpeg', 'ffmpeg.exe'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            return path
            
    return 'ffmpeg'  # Default to PATH
