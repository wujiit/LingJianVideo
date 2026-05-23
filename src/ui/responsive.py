"""
Responsive UI helpers for adapting the desktop layout to different screens.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class UiMetrics:
    profile: str
    scale: float
    available_width: int
    available_height: int

    def px(self, value: int, minimum: int = 1) -> int:
        return max(minimum, int(round(value * self.scale)))

    def choose(self, compact_value, standard_value=None, large_value=None):
        if standard_value is None:
            standard_value = compact_value
        if self.profile == "compact":
            return compact_value
        if self.profile == "large" and large_value is not None:
            return large_value
        return standard_value

    def bounded_width(self, preferred: int, minimum: int, padding: int = 48) -> int:
        max_width = max(minimum, self.available_width - self.px(padding))
        return min(max_width, max(minimum, self.px(preferred)))

    def bounded_height(self, preferred: int, minimum: int, padding: int = 48) -> int:
        max_height = max(minimum, self.available_height - self.px(padding))
        return min(max_height, max(minimum, self.px(preferred)))

    def bounded_size(
        self,
        preferred_width: int,
        preferred_height: int,
        minimum_width: int,
        minimum_height: int,
        padding: int = 48,
    ) -> tuple[int, int]:
        return (
            self.bounded_width(preferred_width, minimum_width, padding),
            self.bounded_height(preferred_height, minimum_height, padding),
        )


def detect_ui_metrics(screen=None) -> UiMetrics:
    app = QApplication.instance()
    active_screen = screen or (app.primaryScreen() if app else None)

    if active_screen is None:
        width, height = 1600, 900
    else:
        geometry = active_screen.availableGeometry()
        width, height = geometry.width(), geometry.height()

    width_ratio = width / 1600.0
    height_ratio = height / 900.0
    scale = max(0.86, min(1.08, min(width_ratio, height_ratio)))

    if scale < 0.95:
        profile = "compact"
    elif scale > 1.04:
        profile = "large"
    else:
        profile = "standard"

    return UiMetrics(
        profile=profile,
        scale=scale,
        available_width=width,
        available_height=height,
    )


def apply_app_font(app: QApplication | None, metrics: UiMetrics) -> None:
    if app is None:
        return

    font = QFont("Microsoft YaHei UI", metrics.choose(9, 10, 11))
    try:
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    except AttributeError:
        font.setHintingPreference(QFont.PreferFullHinting)
    try:
        font.setWeight(QFont.Weight.Medium)
    except AttributeError:
        font.setWeight(QFont.Medium)
    app.setFont(font)
