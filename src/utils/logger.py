"""
Logger for application logging
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from collections import deque


class Logger:
    """Application logger with memory buffer"""
    
    _instance: Optional['Logger'] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir: str = None, max_buffer: int = 500):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._log_dir = Path(log_dir) if log_dir else Path.home() / '.vda' / 'logs'
        self._max_buffer = max_buffer
        self._buffer: deque = deque(maxlen=max_buffer)
        self._callbacks: list = []
        
        # Create log directory
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Python logger
        self._logger = logging.getLogger('VideoDownloadAssistant')
        self._logger.setLevel(logging.DEBUG)
        
        # File handler
        log_file = self._log_dir / f"vda_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self._logger.addHandler(file_handler)
    
    def add_callback(self, callback: Callable[[str, str, str], None]):
        """
        Add callback for log events
        
        Args:
            callback: Function(level, message, timestamp)
        """
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove a callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _log(self, level: str, message: str):
        """Internal log method"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        entry = {
            'level': level,
            'message': message,
            'timestamp': timestamp,
            'full_timestamp': datetime.now().isoformat(),
        }
        self._buffer.append(entry)
        
        # Log to file
        log_func = getattr(self._logger, level.lower(), self._logger.info)
        log_func(message)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(level, message, timestamp)
            except:
                pass
    
    def debug(self, message: str):
        """Log debug message"""
        self._log('DEBUG', message)
    
    def info(self, message: str):
        """Log info message"""
        self._log('INFO', message)
    
    def warning(self, message: str):
        """Log warning message"""
        self._log('WARNING', message)
    
    def error(self, message: str):
        """Log error message"""
        self._log('ERROR', message)
    
    def success(self, message: str):
        """Log success message (custom level)"""
        self._log('SUCCESS', message)
    
    def get_logs(self, count: int = 100, level: str = None) -> list:
        """
        Get recent log entries
        
        Args:
            count: Number of entries to return
            level: Filter by level (optional)
            
        Returns:
            List of log entries
        """
        logs = list(self._buffer)
        
        if level:
            logs = [l for l in logs if l['level'] == level]
        
        return logs[-count:]
    
    def clear(self):
        """Clear log buffer"""
        self._buffer.clear()
    
    def get_log_file(self) -> str:
        """Get current log file path"""
        return str(self._log_dir / f"vda_{datetime.now().strftime('%Y%m%d')}.log")
    
    def cleanup_old_logs(self, days: int = 7):
        """Remove log files older than specified days"""
        try:
            cutoff = datetime.now().timestamp() - (days * 86400)
            for log_file in self._log_dir.glob('vda_*.log'):
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
        except:
            pass

    def shutdown(self):
        """Flush and close logger handlers so Windows file locks are released."""
        callbacks = list(self._callbacks)
        self._callbacks.clear()

        for handler in list(self._logger.handlers):
            try:
                handler.flush()
            except Exception:
                pass
            try:
                handler.close()
            except Exception:
                pass
            try:
                self._logger.removeHandler(handler)
            except Exception:
                pass

        for callback in callbacks:
            try:
                self.remove_callback(callback)
            except Exception:
                pass

        try:
            logging.shutdown()
        except Exception:
            pass


# Global logger instance
def get_logger() -> Logger:
    """Get global logger instance"""
    return Logger()


def shutdown_logger():
    """Shutdown the global logger only if it has been initialized."""
    if Logger._instance is not None:
        Logger._instance.shutdown()
