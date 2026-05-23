"""
Settings dialog
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout

from services.config_manager import ConfigManager
from ui.responsive import detect_ui_metrics
from ui.widgets.settings_widget import SettingsWidget


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        metrics = detect_ui_metrics(parent.screen() if parent else None)
        width, height = metrics.bounded_size(600, 700, 460, 540, padding=36)
        min_width, min_height = metrics.bounded_size(520, 620, 420, 500, padding=24)
        self.resize(width, height)
        self.setMinimumSize(min_width, min_height)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.widget = SettingsWidget(self.config)
        self.widget.settings_changed.connect(self.accept)
        layout.addWidget(self.widget)
