"""
Log widget for displaying application logs
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTextEdit,
    QPushButton, QLabel
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCharFormat, QColor, QFont

from utils.logger import Logger, get_logger
from services.config_manager import ConfigManager


class LogWidget(QWidget):
    """Widget for displaying application logs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger()
        self._config = getattr(parent, "_config", None) or ConfigManager()
        self._setup_ui()
        self._connect_logger()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Log Group
        log_group = QGroupBox()
        log_layout = QVBoxLayout(log_group)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📋 状态日志")
        title_label.setObjectName("sectionLabel")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        clear_btn = QPushButton("清空")
        clear_btn.setFixedWidth(60)
        clear_btn.setObjectName("ghost")
        clear_btn.clicked.connect(self._clear_logs)
        header_layout.addWidget(clear_btn)
        
        log_layout.addLayout(header_layout)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Consolas", 12))
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    def _connect_logger(self):
        """Connect to logger callbacks"""
        self._logger.add_callback(self._on_log)
        
        # Load existing logs
        for entry in self._logger.get_logs(50):
            self._append_log(
                entry['level'],
                entry['message'],
                entry['timestamp']
            )
    
    def _on_log(self, level: str, message: str, timestamp: str):
        """Handle new log entry"""
        self._append_log(level, message, timestamp)
    
    def _append_log(self, level: str, message: str, timestamp: str):
        """Append a log entry to the display"""
        theme = self._get_theme()
        if theme == "light":
            colors = {
                'DEBUG': '#475569',
                'INFO': '#334155',
                'WARNING': '#b45309',
                'ERROR': '#dc2626',
                'SUCCESS': '#16a34a',
                'timestamp': '#64748b',
            }
        else:
            colors = {
                'DEBUG': '#666666',
                'INFO': '#a0a0a0',
                'WARNING': '#ffc107',
                'ERROR': '#ff6b6b',
                'SUCCESS': '#51cf66',
                'timestamp': '#666666',
            }
        color = colors.get(level, colors['INFO'])
        html = f'<span style="color: {colors["timestamp"]};">[{timestamp}]</span> '
        html += f'<span style="color: {color};">{message}</span>'
        
        self.log_text.append(html)
        
        # Auto scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _get_theme(self) -> str:
        if self._config:
            return self._config.get('theme', 'dark')
        return 'dark'
    
    def _clear_logs(self):
        """Clear the log display"""
        self.log_text.clear()
        self._logger.clear()
    
    def info(self, message: str):
        """Log an info message"""
        self._logger.info(message)
    
    def success(self, message: str):
        """Log a success message"""
        self._logger.success(message)
    
    def warning(self, message: str):
        """Log a warning message"""
        self._logger.warning(message)
    
    def error(self, message: str):
        """Log an error message"""
        self._logger.error(message)
