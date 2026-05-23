"""
File utilities for file operations
"""
import os
import re
import shutil
from pathlib import Path
from typing import Optional, List


class FileUtils:
    """File operation utilities"""
    
    # Illegal characters for Windows filenames
    ILLEGAL_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
    
    # Reserved Windows filenames
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
    }
    
    @staticmethod
    def clean_filename(filename: str, max_length: int = 200) -> str:
        """
        Clean filename by removing illegal characters
        
        Args:
            filename: Original filename
            max_length: Maximum filename length
            
        Returns:
            Cleaned filename
        """
        if not filename:
            return "download"
        
        # Remove illegal characters
        cleaned = re.sub(FileUtils.ILLEGAL_CHARS, '_', filename)
        
        # Remove leading/trailing dots and spaces
        cleaned = cleaned.strip('. ')
        
        # Replace multiple underscores/spaces
        cleaned = re.sub(r'[_\s]+', ' ', cleaned)
        
        # Handle reserved names
        name_upper = cleaned.upper().split('.')[0]
        if name_upper in FileUtils.RESERVED_NAMES:
            cleaned = '_' + cleaned
        
        # Truncate if too long (keep extension)
        if len(cleaned) > max_length:
            parts = cleaned.rsplit('.', 1)
            if len(parts) == 2 and len(parts[1]) <= 10:
                name, ext = parts
                cleaned = name[:max_length - len(ext) - 1] + '.' + ext
            else:
                cleaned = cleaned[:max_length]
        
        return cleaned if cleaned else "download"
    
    @staticmethod
    def ensure_unique_filename(filepath: str) -> str:
        """
        Ensure filename is unique by adding number suffix if needed
        
        Args:
            filepath: Desired file path
            
        Returns:
            Unique file path
        """
        if not os.path.exists(filepath):
            return filepath
        
        path = Path(filepath)
        name = path.stem
        ext = path.suffix
        parent = path.parent
        
        counter = 1
        while True:
            new_name = f"{name} ({counter}){ext}"
            new_path = parent / new_name
            if not new_path.exists():
                return str(new_path)
            counter += 1
            if counter > 1000:  # Safety limit
                break
        
        return filepath
    
    @staticmethod
    def get_file_size(filepath: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(filepath)
        except:
            return 0
    
    @staticmethod
    def get_file_size_str(filepath: str) -> str:
        """Get human-readable file size"""
        size = FileUtils.get_file_size(filepath)
        return FileUtils.format_bytes(size)
    
    @staticmethod
    def format_bytes(size: int) -> str:
        """Format bytes to human-readable string"""
        if size <= 0:
            return "0 B"
        elif size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
    
    @staticmethod
    def ensure_dir(path: str) -> bool:
        """
        Ensure directory exists, create if needed
        
        Args:
            path: Directory path
            
        Returns:
            True if directory exists or was created
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except:
            return False
    
    @staticmethod
    def get_free_space(path: str) -> int:
        """
        Get free disk space in bytes
        
        Args:
            path: Path on the disk to check
            
        Returns:
            Free space in bytes
        """
        try:
            if os.name == 'nt':
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes)
                )
                return free_bytes.value
            else:
                stat = os.statvfs(path)
                return stat.f_bavail * stat.f_frsize
        except:
            return 0
    
    @staticmethod
    def has_enough_space(path: str, required_bytes: int) -> bool:
        """Check if there's enough disk space"""
        free = FileUtils.get_free_space(path)
        return free >= required_bytes * 1.1  # 10% buffer
    
    @staticmethod
    def delete_file(filepath: str) -> bool:
        """Delete a file safely"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        except:
            return False
    
    @staticmethod
    def move_file(src: str, dst: str) -> bool:
        """Move a file"""
        try:
            shutil.move(src, dst)
            return True
        except:
            return False
    
    @staticmethod
    def copy_file(src: str, dst: str) -> bool:
        """Copy a file"""
        try:
            shutil.copy2(src, dst)
            return True
        except:
            return False
    
    @staticmethod
    def list_files(directory: str, extensions: List[str] = None) -> List[str]:
        """
        List files in directory
        
        Args:
            directory: Directory path
            extensions: Filter by extensions (e.g., ['.mp4', '.mkv'])
            
        Returns:
            List of file paths
        """
        files = []
        try:
            for entry in os.scandir(directory):
                if entry.is_file():
                    if extensions:
                        ext = Path(entry.path).suffix.lower()
                        if ext in extensions:
                            files.append(entry.path)
                    else:
                        files.append(entry.path)
        except:
            pass
        return files
    
    @staticmethod
    def open_folder(path: str) -> bool:
        """Open folder in file explorer"""
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif os.name == 'posix':
                import subprocess
                subprocess.run(['xdg-open', path])
            return True
        except:
            return False
    
    @staticmethod
    def open_file(filepath: str) -> bool:
        """Open file with default application"""
        try:
            if os.name == 'nt':
                os.startfile(filepath)
            elif os.name == 'posix':
                import subprocess
                subprocess.run(['xdg-open', filepath])
            return True
        except:
            return False
    
    @staticmethod
    def resource_path(relative_path: str) -> str:
        """Get absolute path to resource, works for dev and for PyInstaller"""
        import sys
        if hasattr(sys, '_MEIPASS'):
            # Running as compiled exe - resources are in _MEIPASS
            return os.path.join(sys._MEIPASS, relative_path)
        else:
            # Running as script - look in project root (one level up from src)
            # __file__ is in src/utils/file_utils.py, so go up 3 levels to project root
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
            return os.path.join(project_root, relative_path)

