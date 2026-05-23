"""
Standalone log dialog
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from services.config_manager import ConfigManager
from ui.responsive import detect_ui_metrics
from utils.logger import get_logger


class LogDialog(QDialog):
    """Standalone log viewer dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger()
        self._config = getattr(parent, "_config", None) or ConfigManager()
        self._setup_ui()
        self._connect_logger()

    def _setup_ui(self):
        self.setWindowTitle("状态日志")
        metrics = detect_ui_metrics(self.parent().screen() if self.parent() else None)
        pref_width, pref_height = metrics.bounded_size(700, 500, 520, 380, padding=36)
        min_width, min_height = metrics.bounded_size(600, 400, 460, 340, padding=24)
        self.setMinimumSize(min_width, min_height)
        self.resize(pref_width, pref_height)
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_label = QLabel("应用程序日志")
        title_label.setObjectName("sectionLabel")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        clear_btn = QPushButton("清空日志")
        clear_btn.setFixedWidth(100)
        clear_btn.setObjectName("ghost")
        clear_btn.clicked.connect(self._clear_logs)
        header_layout.addWidget(clear_btn)
        layout.addLayout(header_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 12))
        layout.addWidget(self.log_text)

        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(80)
        close_btn.setObjectName("ghost")
        close_btn.clicked.connect(self.hide)
        footer_layout.addWidget(close_btn)

        layout.addLayout(footer_layout)

    def _connect_logger(self):
        self._logger.add_callback(self._on_log)
        for entry in self._logger.get_logs(100):
            self._append_log(entry["level"], entry["message"], entry["timestamp"])

    def _on_log(self, level: str, message: str, timestamp: str):
        self._append_log(level, message, timestamp)

    def _append_log(self, level: str, message: str, timestamp: str):
        theme = self._get_theme()
        if theme == "light":
            colors = {
                "DEBUG": "#475569",
                "INFO": "#334155",
                "WARNING": "#b45309",
                "ERROR": "#dc2626",
                "SUCCESS": "#16a34a",
                "timestamp": "#64748b",
            }
        else:
            colors = {
                "DEBUG": "#666666",
                "INFO": "#a0a0a0",
                "WARNING": "#ffc107",
                "ERROR": "#ff6b6b",
                "SUCCESS": "#51cf66",
                "timestamp": "#666666",
            }

        color = colors.get(level, colors["INFO"])
        html = f'<span style="color: {colors["timestamp"]};">[{timestamp}]</span> '
        html += f'<span style="color: {color};">{message}</span>'
        self.log_text.append(html)

        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _get_theme(self) -> str:
        if self._config:
            return self._config.get("theme", "dark")
        return "dark"

    def _clear_logs(self):
        self.log_text.clear()
        self._logger.clear()

    def showEvent(self, event):
        super().showEvent(event)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
