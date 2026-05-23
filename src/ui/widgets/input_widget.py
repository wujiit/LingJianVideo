"""
Input widget for URL input and video info display.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QGroupBox, QApplication, QGridLayout
)
from PySide6.QtCore import Signal, Qt, QThread
from PySide6.QtGui import QPixmap

from core.ytdlp_wrapper import YtdlpWrapper
from core.video_info import VideoInfo


class ParseWorker(QThread):
    """Worker thread for parsing video info."""

    finished = Signal(object, str)  # VideoInfo or None, error message

    def __init__(self, url: str, wrapper: YtdlpWrapper):
        super().__init__()
        self.url = url
        self.wrapper = wrapper

    def run(self):
        try:
            info = self.wrapper.get_video_info(self.url)
            self.finished.emit(info, "")
        except Exception as e:
            self.finished.emit(None, str(e))


class ThumbnailWorker(QThread):
    """Worker thread for loading thumbnails."""

    finished = Signal(str, bytes, str)  # url, image bytes, error

    def __init__(self, url: str, timeout: int = 5):
        super().__init__()
        self.url = url
        self.timeout = timeout

    def run(self):
        try:
            import requests

            response = requests.get(self.url, timeout=self.timeout)
            if response.status_code == 200:
                self.finished.emit(self.url, response.content, "")
            else:
                self.finished.emit(self.url, b"", f"HTTP {response.status_code}")
        except Exception as e:
            self.finished.emit(self.url, b"", str(e))


class InputWidget(QWidget):
    """Widget for URL input and video info preview."""

    video_parsed = Signal(VideoInfo)
    parse_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._wrapper = YtdlpWrapper()
        self._worker = None
        self._thumbnail_worker = None
        self._video_info = None
        self._parse_request_token = 0
        self._active_parse_token = None
        self._thumbnail_request_token = 0
        self._active_thumbnail_token = None
        self._thumbnail_cache = {}
        self._background_workers = set()
        self._status_tone = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        input_group = QGroupBox("Video URL")
        input_layout = QVBoxLayout(input_group)

        url_row = QHBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a video URL here...")
        self.url_input.returnPressed.connect(self._parse_url)
        url_row.addWidget(self.url_input, 1)

        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setFixedWidth(80)
        self.paste_btn.clicked.connect(self._paste_from_clipboard)
        url_row.addWidget(self.paste_btn)

        self.parse_btn = QPushButton("Parse")
        self.parse_btn.setObjectName("primary")
        self.parse_btn.setFixedWidth(80)
        self.parse_btn.clicked.connect(self._parse_url)
        url_row.addWidget(self.parse_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(80)
        self.clear_btn.clicked.connect(self._clear)
        url_row.addWidget(self.clear_btn)

        input_layout.addLayout(url_row)

        self.status_label = QLabel("Enter a link to parse video information.")
        self.status_label.setObjectName("status")
        input_layout.addWidget(self.status_label)

        layout.addWidget(input_group)

        self.info_group = QGroupBox("Video Info")
        self.info_group.setMinimumHeight(150)

        info_layout = QHBoxLayout(self.info_group)
        info_layout.setSpacing(16)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(240, 135)
        self.thumbnail_label.setObjectName("thumbnail")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setText("Waiting for parse...")
        info_layout.addWidget(self.thumbnail_label)

        details_widget = QWidget()
        details_grid = QGridLayout(details_widget)
        details_grid.setContentsMargins(0, 0, 0, 0)
        details_grid.setVerticalSpacing(8)
        details_grid.setHorizontalSpacing(16)

        self.title_label = QLabel("Waiting for video parse...")
        self.title_label.setObjectName("videoTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        details_grid.addWidget(self.title_label, 0, 0, 1, 4)

        self.author_label = QLabel("Author: -")
        details_grid.addWidget(self.author_label, 1, 0)

        self.duration_label = QLabel("Duration: -")
        details_grid.addWidget(self.duration_label, 1, 1)

        self.site_label = QLabel("Source: -")
        details_grid.addWidget(self.site_label, 1, 2)

        self.quality_label = QLabel("Quality: -")
        details_grid.addWidget(self.quality_label, 2, 0)

        self.size_label = QLabel("Size: -")
        details_grid.addWidget(self.size_label, 2, 1)

        details_grid.setRowStretch(3, 1)
        info_layout.addWidget(details_widget, 1)

        self.info_group.setVisible(False)
        layout.addWidget(self.info_group)

    def _paste_from_clipboard(self):
        """Paste URL from clipboard."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.url_input.setText(text)
            if text.startswith("http"):
                self._parse_url()

    def _parse_url(self):
        """Parse the entered URL."""
        url = self.url_input.text().strip()
        if not url:
            self._set_status("Please enter a video link.", "error")
            return

        if not self._wrapper.validate_url(url):
            self._set_status("Invalid link format. Please check the URL.", "error")
            return

        self.parse_btn.setEnabled(False)
        self._set_status("Parsing video information...", "status")
        self._parse_request_token += 1
        token = self._parse_request_token
        self._active_parse_token = token
        self._active_thumbnail_token = None

        worker = ParseWorker(url, self._wrapper)
        self._worker = worker
        self._retain_background_worker(worker)
        worker.finished.connect(lambda info, error, token=token: self._on_parse_finished(token, info, error))
        worker.finished.connect(lambda *_args, worker=worker: self._release_background_worker(worker))
        worker.start()

    def _on_parse_finished(self, token: int, info: VideoInfo, error: str):
        """Handle parse completion."""
        if token != self._active_parse_token:
            return

        self._active_parse_token = None
        self.parse_btn.setEnabled(True)

        if error:
            self._set_status(f"Parse failed: {error}", "error")
            self.info_group.setVisible(False)
            self.parse_error.emit(error)
            return

        if not info:
            self._set_status("Could not fetch video information.", "error")
            self.info_group.setVisible(False)
            return

        self._video_info = info
        self._set_status("Parse successful.", "success")
        self._update_info_display(info)
        self.info_group.setVisible(True)
        self.video_parsed.emit(info)

    def _update_info_display(self, info: VideoInfo):
        """Update the video info display."""
        title = info.title[:100] + "..." if len(info.title) > 100 else info.title
        self.title_label.setText(title)
        self.author_label.setText(f"Author: {info.author or 'Unknown'}")
        self.duration_label.setText(f"Duration: {info.duration_str}")
        self.site_label.setText(f"Source: {info.site_name}")

        resolutions = info.available_resolutions
        self.quality_label.setText(f"Quality: {resolutions[0] if resolutions else 'Unknown'}")

        estimated = info.estimate_size()
        self.size_label.setText(f"Size: ~{estimated:.1f} MB" if estimated > 0 else "Size: Unknown")

        if info.thumbnail:
            self._load_thumbnail(info.thumbnail)
        else:
            self._active_thumbnail_token = None
            self._set_thumbnail_placeholder("No thumbnail")

    def _load_thumbnail(self, url: str):
        """Load thumbnail image asynchronously."""
        self._thumbnail_request_token += 1
        token = self._thumbnail_request_token
        self._active_thumbnail_token = token

        cached = self._thumbnail_cache.get(url)
        if cached is not None:
            self._apply_thumbnail_data(cached)
            return

        self._set_thumbnail_placeholder("Loading thumbnail...")
        worker = ThumbnailWorker(url)
        self._thumbnail_worker = worker
        self._retain_background_worker(worker)
        worker.finished.connect(
            lambda loaded_url, data, error, token=token: self._on_thumbnail_finished(
                token, loaded_url, data, error
            )
        )
        worker.finished.connect(lambda *_args, worker=worker: self._release_background_worker(worker))
        worker.start()

    def _on_thumbnail_finished(self, token: int, url: str, data: bytes, error: str):
        if token != self._active_thumbnail_token:
            return
        if error or not data:
            self._set_thumbnail_placeholder("No thumbnail")
            return

        self._cache_thumbnail(url, data)
        self._apply_thumbnail_data(data)

    def _clear(self):
        """Clear input and info."""
        self.url_input.clear()
        self.parse_btn.setEnabled(True)
        self._set_status("", "status")
        self.info_group.setVisible(False)
        self._video_info = None
        self._active_parse_token = None
        self._active_thumbnail_token = None
        self._set_thumbnail_placeholder("Waiting for parse...")

    def _set_status(self, text: str, tone: str):
        if self.status_label.text() != text:
            self.status_label.setText(text)
        if self._status_tone != tone:
            self._status_tone = tone
            self.status_label.setObjectName(tone)
            self._refresh_style(self.status_label)

    def _set_thumbnail_placeholder(self, text: str):
        self.thumbnail_label.setPixmap(QPixmap())
        if self.thumbnail_label.text() != text:
            self.thumbnail_label.setText(text)

    def _apply_thumbnail_data(self, data: bytes):
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            self._set_thumbnail_placeholder("No thumbnail")
            return

        target_w, target_h = 240, 135
        scaled = pixmap.scaled(
            target_w,
            target_h,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        x = (scaled.width() - target_w) // 2
        y = (scaled.height() - target_h) // 2
        if self.thumbnail_label.text():
            self.thumbnail_label.setText("")
        self.thumbnail_label.setPixmap(scaled.copy(x, y, target_w, target_h))

    def _cache_thumbnail(self, url: str, data: bytes):
        if url in self._thumbnail_cache:
            self._thumbnail_cache.pop(url)
        self._thumbnail_cache[url] = data
        while len(self._thumbnail_cache) > 16:
            oldest = next(iter(self._thumbnail_cache))
            self._thumbnail_cache.pop(oldest)

    def _retain_background_worker(self, worker):
        self._background_workers.add(worker)

    def _release_background_worker(self, worker):
        self._background_workers.discard(worker)
        if worker is self._worker:
            self._worker = None
        if worker is self._thumbnail_worker:
            self._thumbnail_worker = None
        worker.deleteLater()

    def _refresh_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    @property
    def video_info(self) -> VideoInfo:
        """Get current video info."""
        return self._video_info

    @property
    def url(self) -> str:
        """Get current URL."""
        return self.url_input.text().strip()
