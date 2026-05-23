"""
Configuration manager for application settings
"""
import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, Signal


# Default configuration
DEFAULT_CONFIG = {
    # Download settings
    'download_path': str(Path.home() / 'Downloads' / 'Videos'),
    'output_format': 'mp4',
    'naming_rule': '{title}',
    'max_concurrent': 3,
    
    # Quality settings
    'default_quality': 'best',
    'preferred_codec': 'h264',
    'max_resolution': '2160p',
    
    # Audio settings
    'extract_audio_format': 'mp3',
    'audio_quality': '192',
    
    # Network settings
    'proxy': '',
    'use_aria2': False,
    'aria2_path': '',
    'aria2_args': '',
    'rate_limit': '',
    'cookies_from_browser': 'none',
    'cookies_file': '',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'referer': '',
    'request_timeout': 15,
    'fragment_retries': 3,
    'sleep_interval': 0,
    'max_sleep_interval': 0,
    'retry_sleep': '',
    'concurrent_fragments': 0,
    
    # Update settings
    'auto_update_ytdlp': True,
    'check_update_interval': 7,  # days
    
    # UI settings
    'show_advanced': False,
    'language': 'zh_CN',
    'theme': 'dark',
    'minimize_to_tray': False,
    'start_minimized': False,
    
    # First run
    'first_run': True,
    'disclaimer_accepted': False,
    
    # Paths
    'ffmpeg_path': '',
    'ytdlp_path': '',
    'cookies_file': '',
    
    # History
    'recent_urls': [],
    'download_history_days': 30,
}


class ConfigManager(QObject):
    """Manager for application configuration"""
    
    config_changed = Signal(str, object)  # key, new_value
    
    def __init__(self, config_dir: str = None):
        super().__init__()
        
        # Determine config directory
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            # Default to user's app data
            app_data = os.environ.get('APPDATA', str(Path.home()))
            self._config_dir = Path(app_data) / 'VideoDownloadAssistant'
        
        self._config_file = self._config_dir / 'config.json'
        self._config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self._cached_ffmpeg_path: Optional[str] = None
        
        # Ensure config directory exists
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load config
        self.load()
    
    @property
    def config_dir(self) -> Path:
        """Get config directory path"""
        return self._config_dir
    
    def load(self) -> bool:
        """Load configuration from file"""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults (to handle new config keys)
                    self._config = {**DEFAULT_CONFIG, **loaded}
                self._cached_ffmpeg_path = None
                return True
        except Exception as e:
            print(f"Error loading config: {e}")
        return False
    
    def save(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """Set a configuration value"""
        old_value = self._config.get(key)
        self._config[key] = value

        if key == 'ffmpeg_path':
            self._cached_ffmpeg_path = None
        
        if old_value != value:
            self.config_changed.emit(key, value)
        
        if save:
            return self.save()
        return True
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration"""
        return self._config.copy()
    
    def reset(self, key: str = None) -> bool:
        """Reset configuration to default"""
        if key:
            if key in DEFAULT_CONFIG:
                self._config[key] = DEFAULT_CONFIG[key]
                if key == 'ffmpeg_path':
                    self._cached_ffmpeg_path = None
                self.config_changed.emit(key, DEFAULT_CONFIG[key])
        else:
            self._config = DEFAULT_CONFIG.copy()
            self._cached_ffmpeg_path = None
        return self.save()
    
    def get_download_path(self) -> str:
        """Get download path, creating if needed"""
        path = self.get('download_path', DEFAULT_CONFIG['download_path'])
        Path(path).mkdir(parents=True, exist_ok=True)
        return path
    
    def add_recent_url(self, url: str, max_items: int = 20):
        """Add URL to recent history"""
        recent = self.get('recent_urls', [])
        if url in recent:
            recent.remove(url)
        recent.insert(0, url)
        self.set('recent_urls', recent[:max_items])
    
    def get_output_template(self) -> str:
        """Get the yt-dlp output template based on naming rule"""
        naming_rule = self.get('naming_rule', '{title}')
        
        # Map user-friendly placeholders to yt-dlp template
        mappings = {
            '{title}': '%(title)s',
            '{author}': '%(uploader)s',
            '{channel}': '%(channel)s',
            '{date}': '%(upload_date)s',
            '{id}': '%(id)s',
            '{resolution}': '%(resolution)s',
        }
        
        template = naming_rule
        for placeholder, ytdlp_var in mappings.items():
            template = template.replace(placeholder, ytdlp_var)
        
        # Add extension
        template += '.%(ext)s'
        
        return template
    
    def get_ffmpeg_path(self) -> str:
        """Get FFmpeg path"""
        if self._cached_ffmpeg_path:
            return self._cached_ffmpeg_path

        # 1. Custom path from config
        path = self.get('ffmpeg_path', '')
        if path and os.path.exists(path):
            self._cached_ffmpeg_path = path
            return path
        
        # 2. Check next to the executable/script (Priority 1)
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            # Add _internal path check for PyInstaller 6+
            preferred_local_paths = [
                os.path.join(base_path, 'ffmpeg-btbN', 'bin', 'ffmpeg.exe'),
                os.path.join(base_path, 'ffmpeg-btbN', 'ffmpeg.exe'),
                os.path.join(base_path, 'ffmpeg-gyan', 'bin', 'ffmpeg.exe'),
                os.path.join(base_path, 'ffmpeg-gyan', 'ffmpeg.exe'),
            ]
            local_paths = preferred_local_paths + [
                os.path.join(base_path, 'ffmpeg.exe'),
                os.path.join(base_path, 'bin', 'ffmpeg.exe'),
                os.path.join(base_path, '_internal', 'bin', 'ffmpeg.exe'),
                os.path.join(base_path, 'ffmpeg', 'bin', 'ffmpeg.exe'),
            ]
        else:
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            preferred_local_paths = [
                os.path.join(base_path, 'ffmpeg-btbN', 'bin', 'ffmpeg.exe'),
                os.path.join(base_path, 'ffmpeg-btbN', 'ffmpeg.exe'),
                os.path.join(base_path, 'ffmpeg-gyan', 'bin', 'ffmpeg.exe'),
                os.path.join(base_path, 'ffmpeg-gyan', 'ffmpeg.exe'),
            ]
            local_paths = preferred_local_paths + [
                os.path.join(base_path, 'ffmpeg.exe'),
                os.path.join(base_path, 'bin', 'ffmpeg.exe'),
                os.path.join(base_path, 'ffmpeg', 'bin', 'ffmpeg.exe'),
            ]
            
        for p in local_paths:
            if os.path.exists(p):
                self._cached_ffmpeg_path = p
                return p
        
        # 3. Check bundled path (PyInstaller _MEIPASS)
        if getattr(sys, 'frozen', False):
            bundle_path = sys._MEIPASS
            bundled_paths = [
                os.path.join(bundle_path, 'ffmpeg-btbN', 'bin', 'ffmpeg.exe'),
                os.path.join(bundle_path, 'ffmpeg-btbN', 'ffmpeg.exe'),
                os.path.join(bundle_path, 'ffmpeg-gyan', 'bin', 'ffmpeg.exe'),
                os.path.join(bundle_path, 'ffmpeg-gyan', 'ffmpeg.exe'),
                os.path.join(bundle_path, 'ffmpeg.exe'),
                os.path.join(bundle_path, 'bin', 'ffmpeg.exe'),
            ]
            for p in bundled_paths:
                if os.path.exists(p):
                    self._cached_ffmpeg_path = p
                    return p
        
        # 4. Try common system locations
        common_paths = [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
        ]
        for p in common_paths:
            if os.path.exists(p):
                self._cached_ffmpeg_path = p
                return p
        
        # 5. Fallback to PATH
        self._cached_ffmpeg_path = 'ffmpeg'
        return self._cached_ffmpeg_path
    
    def has_accepted_disclaimer(self) -> bool:
        """Check if user has accepted disclaimer"""
        return self.get('disclaimer_accepted', False)
    
    def accept_disclaimer(self):
        """Mark disclaimer as accepted"""
        self.set('disclaimer_accepted', True)
        self.set('first_run', False)
    
    def is_first_run(self) -> bool:
        """Check if this is the first run"""
        return self.get('first_run', True)
