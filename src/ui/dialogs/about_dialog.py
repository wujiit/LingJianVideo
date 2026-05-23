"""
About dialog showing application information
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from services.config_manager import ConfigManager
from services.update_manager import UpdateManager
from ui.responsive import detect_ui_metrics


class AboutDialog(QDialog):
    """About dialog with version information."""

    def __init__(self, update_manager: UpdateManager, ffmpeg_path: str, parent=None):
        super().__init__(parent)
        self.update_manager = update_manager
        self.ffmpeg_path = ffmpeg_path
        self._config = getattr(parent, "_config", None) or ConfigManager()
        self._has_update = False
        self._is_updating = False
        self.setWindowTitle("关于")
        metrics = detect_ui_metrics(parent.screen() if parent else None)
        width, height = metrics.bounded_size(600, 500, 460, 420, padding=36)
        self.resize(width, height)
        self.setMinimumSize(metrics.bounded_width(460, 400, 24), metrics.bounded_height(420, 360, 24))
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        header_layout = QHBoxLayout()

        icon_label = QLabel("i")
        icon_label.setObjectName("dialogIcon")
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_label = QLabel("灵简视频助手")
        title_label.setObjectName("dialogTitle")
        title_layout.addWidget(title_label)

        app_version = QApplication.applicationVersion() or "2.0"
        subtitle_label = QLabel(f"v{app_version} | Lingjian Video Downloader")
        subtitle_label.setObjectName("dialogSubtitle")
        title_layout.addWidget(subtitle_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        version_group = QGroupBox("核心组件版本")
        version_group.setObjectName("panelCard")
        version_layout = QVBoxLayout(version_group)

        ytdlp_row = QHBoxLayout()
        ytdlp_row.addWidget(QLabel("yt-dlp 版本:"))
        ytdlp_row.addStretch()
        self.ytdlp_label = QLabel(self.update_manager.get_ytdlp_version())
        ytdlp_row.addWidget(self.ytdlp_label)
        version_layout.addLayout(ytdlp_row)

        ffmpeg_row = QHBoxLayout()
        ffmpeg_row.addWidget(QLabel("FFmpeg 版本:"))
        ffmpeg_row.addStretch()
        self.ffmpeg_label = QLabel(self.update_manager.get_ffmpeg_version(self.ffmpeg_path))
        ffmpeg_row.addWidget(self.ffmpeg_label)
        version_layout.addLayout(ffmpeg_row)

        layout.addWidget(version_group)

        update_group = QGroupBox("组件更新")
        update_group.setObjectName("panelCard")
        update_layout = QVBoxLayout(update_group)

        self.update_status = QLabel("点击检查更新（仅更新 yt-dlp 内核）")
        self.update_status.setObjectName("muted")
        update_layout.addWidget(self.update_status)

        self.update_progress_bar = QProgressBar()
        self.update_progress_bar.setRange(0, 100)
        self.update_progress_bar.setValue(0)
        self.update_progress_bar.setVisible(False)
        update_layout.addWidget(self.update_progress_bar)

        update_btn_layout = QHBoxLayout()

        self.check_btn = QPushButton("检查内核更新")
        self.check_btn.setObjectName("ghost")
        self.check_btn.clicked.connect(self._check_update)
        update_btn_layout.addWidget(self.check_btn)

        self.update_btn = QPushButton("立即更新")
        self.update_btn.setObjectName("primary")
        self.update_btn.setEnabled(False)
        self.update_btn.clicked.connect(self._apply_update)
        update_btn_layout.addWidget(self.update_btn)

        self.cancel_update_btn = QPushButton("取消更新")
        self.cancel_update_btn.setObjectName("ghost")
        self.cancel_update_btn.setVisible(False)
        self.cancel_update_btn.clicked.connect(self._cancel_update)
        update_btn_layout.addWidget(self.cancel_update_btn)

        update_layout.addLayout(update_btn_layout)
        layout.addWidget(update_group)

        contact_group = QGroupBox("关于作者 / 开源协议")
        contact_group.setObjectName("panelCard")
        contact_layout = QVBoxLayout(contact_group)

        contact_label = QLabel(
            "Designed & Developed by 灵简AI\n"
            "Email: iticu@qq.com\n"
            "微信/QQ: 19577566\n"
            "网站: https://www.jingxialai.com\n"
            "GitHub: https://github.com/wujiit\n\n"
            "------------------------------------------------\n"
            "开源协议: Apache License 2.0\n"
            "本软件完全免费开源，禁止用于非法用途。"
        )
        contact_label.setObjectName("muted")
        contact_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        contact_label.setOpenExternalLinks(True)
        contact_layout.addWidget(contact_label)

        layout.addWidget(contact_group)

        credits_label = QLabel(
            "基于 <a href='https://github.com/yt-dlp/yt-dlp'>yt-dlp</a> 和 "
            "<a href='https://ffmpeg.org'>FFmpeg</a> 开发"
        )
        credits_label.setOpenExternalLinks(True)
        credits_label.setObjectName("muted")
        credits_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(credits_label)

        layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(24, 16, 24, 16)

        terms_btn = QPushButton("使用条款")
        terms_btn.setObjectName("ghost")
        terms_btn.clicked.connect(self._show_terms)
        btn_layout.addWidget(terms_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("ghost")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        main_layout.addWidget(btn_container)

        self.update_manager.update_progress.connect(self._on_update_progress)
        self.update_manager.update_download_progress.connect(
            self._on_update_download_progress
        )
        self.update_manager.update_completed.connect(self._on_update_completed)
        self.update_manager.update_available.connect(self._on_update_available)

    def _show_terms(self):
        """Show terms of use."""
        from ui.dialogs.disclaimer_dialog import DisclaimerDialog

        dialog = DisclaimerDialog(self)
        dialog.exec()

    def _check_update(self):
        """Check for yt-dlp updates."""
        self._has_update = False
        self._is_updating = False
        self.update_status.setText("正在检查更新...")
        self._set_status_tone("status")
        self.update_progress_bar.setVisible(False)
        self.update_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        started = self.update_manager.check_update()
        if not started:
            self.check_btn.setEnabled(True)
            self.update_status.setText("已有更新任务在进行中，请稍后")
            self._set_status_tone("warning")

    def _apply_update(self):
        """Apply yt-dlp update."""
        self.update_status.setText("正在更新...")
        self._set_status_tone("status")
        self.update_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.cancel_update_btn.setVisible(True)
        self.cancel_update_btn.setEnabled(True)
        self.update_progress_bar.setVisible(True)
        self.update_progress_bar.setRange(0, 100)
        self.update_progress_bar.setValue(0)
        self._is_updating = True
        started = self.update_manager.apply_update()
        if not started:
            self._is_updating = False
            self.check_btn.setEnabled(True)
            self.cancel_update_btn.setVisible(False)
            self.update_status.setText("已有更新任务在进行中，请稍后")
            self._set_status_tone("warning")

    def _cancel_update(self):
        """Cancel current update operation."""
        if self._is_updating:
            self.update_manager.cancel()
            self.update_status.setText("正在取消更新...")
            self._set_status_tone("warning")
            self.cancel_update_btn.setEnabled(False)

    def _on_update_progress(self, message: str):
        """Handle update progress."""
        self.update_status.setText(message)

    def _on_update_download_progress(self, percent: int, downloaded: int, total: int):
        """Handle update download progress for progress bar."""
        del downloaded, total

        if not self._is_updating:
            return

        self.update_progress_bar.setVisible(True)
        if percent < 0:
            self.update_progress_bar.setRange(0, 0)
            return

        if self.update_progress_bar.maximum() == 0:
            self.update_progress_bar.setRange(0, 100)
        self.update_progress_bar.setValue(max(0, min(100, percent)))

    def _on_update_completed(self, success: bool, message: str):
        """Handle update completion."""
        was_updating = self._is_updating
        self._is_updating = False
        self.check_btn.setEnabled(True)
        self.cancel_update_btn.setVisible(False)
        self.cancel_update_btn.setEnabled(False)

        if success:
            self.update_status.setText(message)
            if "发现新版本" in message:
                self._set_status_tone("warning")
            else:
                self._set_status_tone("success")
            self.ytdlp_label.setText(self.update_manager.get_ytdlp_version())
            if "更新完成" in message or "已经是最新版本" in message:
                self._has_update = False
        else:
            self.update_status.setText(
                f"{message}；如持续失败，请联系作者获取离线内核包"
            )
            self._set_status_tone("error")
            if was_updating:
                self._has_update = True

        if was_updating:
            if self.update_progress_bar.maximum() == 0:
                self.update_progress_bar.setRange(0, 100)
            if success and "更新完成" in message:
                self.update_progress_bar.setValue(100)
            else:
                self.update_progress_bar.setValue(0)
                self.update_progress_bar.setVisible(False)
        else:
            self.update_progress_bar.setVisible(False)

        self.update_btn.setEnabled(self._has_update)

    def _on_update_available(self, current: str, latest: str):
        """Handle update available."""
        self._has_update = True
        self.update_status.setText(f"发现新版本：{latest}（当前：{current}）")
        self._set_status_tone("warning")
        self.update_btn.setEnabled(True)

    def _set_status_tone(self, tone: str):
        self.update_status.setObjectName(tone)
        self._refresh_style(self.update_status)

    def _refresh_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
