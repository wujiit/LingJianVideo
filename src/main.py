"""
Video Download Assistant - Main Entry Point
"""
import multiprocessing
import os
import sys
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


def get_base_path():
    """Get base path for resources, works both in dev and packaged mode."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _ensure_src_on_path():
    src_path = os.path.dirname(os.path.abspath(__file__))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def _inject_updates():
    try:
        app_data = os.environ.get("APPDATA", str(os.path.expanduser("~")))
        update_dir = os.path.join(app_data, "VideoDownloadAssistant", "updates")

        zip_file = os.path.join(update_dir, "yt_dlp_latest.zip")
        whl_file = os.path.join(update_dir, "yt_dlp_latest.whl")

        target_file = None
        if os.path.exists(zip_file):
            target_file = zip_file
        elif os.path.exists(whl_file):
            target_file = whl_file

        if target_file:
            sys.path.insert(0, target_file)
    except Exception:
        pass


def _cleanup_multiprocessing_children(timeout_ms: int = 1500):
    timeout_seconds = max(timeout_ms, 0) / 1000.0
    children = multiprocessing.active_children()
    if not children:
        return

    deadline = time.monotonic() + timeout_seconds

    for child in children:
        try:
            child.terminate()
        except Exception:
            pass

    for child in children:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            child.join(timeout=remaining)
        except Exception:
            pass

    for child in multiprocessing.active_children():
        try:
            if hasattr(child, "kill"):
                child.kill()
            else:
                child.terminate()
        except Exception:
            pass
        try:
            child.join(timeout=0.5)
        except Exception:
            pass
        try:
            child.close()
        except Exception:
            pass


def main():
    """Main entry point."""
    multiprocessing.freeze_support()
    _ensure_src_on_path()
    _inject_updates()

    from ui.main_window import MainWindow
    from ui.responsive import apply_app_font, detect_ui_metrics
    from utils.file_utils import FileUtils
    from utils.logger import shutdown_logger

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor
    )

    app = QApplication(sys.argv)
    app.setApplicationName("灵简视频助手")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("VideoDownloadAssistant")

    icon_path = FileUtils.resource_path("converted.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    apply_app_font(app, detect_ui_metrics(app.primaryScreen()))

    window = None
    exit_code = 0

    try:
        window = MainWindow()
        window.show()
        exit_code = app.exec()
    finally:
        if window is not None:
            try:
                window.shutdown()
            except Exception:
                pass

        try:
            shutdown_logger()
        except Exception:
            pass

        _cleanup_multiprocessing_children()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
