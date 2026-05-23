"""
Download format options widget.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.download_task import DownloadOptions
from core.media_presets import DOWNLOAD_POST_PROCESS_PRESETS
from core.video_info import VideoInfo


class FormatWidget(QWidget):
    options_changed = Signal(DownloadOptions)
    download_requested = Signal(DownloadOptions)
    mode_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._video_info = None
        self._strategy = None
        self._mode_hint_tone = None
        self._setup_ui()

    def _ensure_strategy(self):
        if self._strategy is None:
            from controllers.smart_strategy import SmartStrategy

            self._strategy = SmartStrategy()
        return self._strategy

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        self._format_group = QGroupBox("下载选项")
        self._format_group.setObjectName("panelCard")
        self._format_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._format_layout = QVBoxLayout(self._format_group)
        self._format_layout.setContentsMargins(12, 10, 12, 12)
        self._format_layout.setSpacing(8)

        self._mode_row = QHBoxLayout()
        self._mode_row.setSpacing(8)
        self._mode_row.addWidget(QLabel("下载模式:"))

        self.mode_group = QButtonGroup(self)
        self.mode_best = QRadioButton("推荐")
        self.mode_best.setChecked(True)
        self.mode_group.addButton(self.mode_best, 0)
        self._mode_row.addWidget(self.mode_best)

        self.mode_custom = QRadioButton("自定义")
        self.mode_group.addButton(self.mode_custom, 1)
        self._mode_row.addWidget(self.mode_custom)

        self.mode_audio = QRadioButton("仅音频")
        self.mode_group.addButton(self.mode_audio, 2)
        self._mode_row.addWidget(self.mode_audio)
        self._mode_row.addStretch()
        self._format_layout.addLayout(self._mode_row)

        self.mode_group.buttonClicked.connect(self._on_mode_changed)

        self.mode_hint = QLabel("")
        self.mode_hint.setWordWrap(True)
        self._format_layout.addWidget(self.mode_hint)

        self.custom_options = QWidget()
        self.custom_options.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._custom_row = QHBoxLayout(self.custom_options)
        self._custom_row.setContentsMargins(0, 0, 0, 0)
        self._custom_row.setSpacing(10)
        self._custom_row.addWidget(QLabel("画质:"))
        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumWidth(90)
        self.quality_combo.currentIndexChanged.connect(self._update_estimate)
        self._custom_row.addWidget(self.quality_combo)
        self._custom_row.addWidget(QLabel("编码:"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["H.264", "H.265", "VP9", "AV1"])
        self.codec_combo.setMinimumWidth(84)
        self._custom_row.addWidget(self.codec_combo)
        self._custom_row.addWidget(QLabel("封装:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "MKV", "WebM"])
        self.format_combo.setMinimumWidth(84)
        self._custom_row.addWidget(self.format_combo)
        self._custom_row.addStretch()
        self._format_layout.addWidget(self.custom_options)

        self.audio_options = QWidget()
        self.audio_options.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._audio_row = QHBoxLayout(self.audio_options)
        self._audio_row.setContentsMargins(0, 0, 0, 0)
        self._audio_row.setSpacing(10)
        self._audio_row.addWidget(QLabel("格式:"))
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["MP3", "M4A", "FLAC", "WAV"])
        self.audio_format_combo.setMinimumWidth(84)
        self._audio_row.addWidget(self.audio_format_combo)
        self._audio_row.addWidget(QLabel("音质:"))
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems(["320k", "256k", "192k", "128k"])
        self.audio_quality_combo.setMinimumWidth(84)
        self._audio_row.addWidget(self.audio_quality_combo)
        self._audio_row.addStretch()
        self._format_layout.addWidget(self.audio_options)

        self._post_row = QHBoxLayout()
        self._post_row.setSpacing(8)
        self._post_row.addWidget(QLabel("下载后处理:"))
        self.post_process_combo = QComboBox()
        for key, preset in DOWNLOAD_POST_PROCESS_PRESETS.items():
            self.post_process_combo.addItem(preset["label"], key)
        self.post_process_combo.currentIndexChanged.connect(self._update_post_process_ui)
        self._post_row.addWidget(self.post_process_combo, 1)

        self.delete_source_check = QCheckBox("处理成功后删除源文件")
        self.delete_source_check.setEnabled(False)
        self._post_row.addWidget(self.delete_source_check)
        self._format_layout.addLayout(self._post_row)

        self.post_process_hint = QLabel(DOWNLOAD_POST_PROCESS_PRESETS["none"]["description"])
        self.post_process_hint.setObjectName("muted")
        self.post_process_hint.setWordWrap(True)
        self._format_layout.addWidget(self.post_process_hint)

        self._bottom_row = QHBoxLayout()
        self._bottom_row.setSpacing(10)

        self.download_btn = QPushButton("加入下载队列")
        self.download_btn.setObjectName("primary")
        self.download_btn.setFixedHeight(38)
        self.download_btn.setFixedWidth(176)
        self.download_btn.clicked.connect(self._on_download_clicked)
        self._bottom_row.addWidget(self.download_btn)

        self._bottom_row.addStretch()

        self.transcode_label = QLabel("")
        self.transcode_label.setObjectName("warning")
        self._bottom_row.addWidget(self.transcode_label)

        self.size_label = QLabel("预计: -")
        self.size_label.setObjectName("muted")
        self._bottom_row.addWidget(self.size_label)

        self._format_layout.addLayout(self._bottom_row)
        self._root_layout.addWidget(self._format_group)

        self._update_post_process_ui()
        self._on_mode_changed()

    def _refresh_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _set_mode_hint(self, text, tone):
        if self.mode_hint.text() != text:
            self.mode_hint.setText(text)
        if self._mode_hint_tone != tone:
            self._mode_hint_tone = tone
            self.mode_hint.setObjectName(tone)
            self._refresh_style(self.mode_hint)

    def set_video_info(self, info: VideoInfo):
        self._video_info = info
        self._update_quality_options()
        self._update_estimate()

    def _update_quality_options(self):
        self.quality_combo.clear()
        if not self._video_info:
            return

        resolutions = self._video_info.available_resolutions
        for resolution in (resolutions if resolutions else ["最佳"]):
            self.quality_combo.addItem(resolution)

    def _on_mode_changed(self):
        mode_id = self.mode_group.checkedId()
        self.custom_options.setVisible(mode_id == 1)
        self.audio_options.setVisible(mode_id == 2)

        if mode_id == 0:
            self._set_mode_hint("自动选择最佳画质和格式", "success")
        elif mode_id == 1:
            self._set_mode_hint("手动选择画质、编码和封装格式。", "muted")
        else:
            self._set_mode_hint("提取音频并导出为指定格式。", "muted")

        self._update_estimate()
        self.mode_changed.emit()

    def _update_post_process_ui(self):
        preset_key = self.post_process_combo.currentData() or "none"
        preset = DOWNLOAD_POST_PROCESS_PRESETS.get(
            preset_key, DOWNLOAD_POST_PROCESS_PRESETS["none"]
        )
        self.post_process_hint.setText(preset.get("description", ""))
        enabled = preset_key != "none"
        self.delete_source_check.setEnabled(enabled)
        if not enabled:
            self.delete_source_check.setChecked(False)

    def _update_estimate(self):
        if not self._video_info:
            self.size_label.setText("预计: -")
            self.transcode_label.setText("")
            return

        mode_id = self.mode_group.checkedId()
        if mode_id == 2:
            best_audio = self._video_info.best_audio_format
            self.size_label.setText(
                f"预计: ~{best_audio.size_mb:.1f}MB" if best_audio else "预计: -"
            )
            self.transcode_label.setText("")
            return

        if mode_id == 1:
            codec_map = {"H.264": "h264", "H.265": "h265", "VP9": "vp9", "AV1": "av1"}
            rec = self._ensure_strategy().recommend_format(
                self._video_info,
                self.quality_combo.currentText(),
                codec_map.get(self.codec_combo.currentText(), "h264"),
            )
        else:
            rec = self._ensure_strategy().recommend_format(self._video_info, "best")

        size = rec.get("estimated_size_mb", 0)
        self.size_label.setText(f"预计: ~{size:.1f}MB" if size > 0 else "预计: -")
        self.transcode_label.setText("需要转码" if rec.get("needs_transcode") else "")

    def _on_download_clicked(self):
        self.download_requested.emit(self.get_options())

    def get_options(self) -> DownloadOptions:
        options = DownloadOptions()
        mode_id = self.mode_group.checkedId()

        if mode_id == 2:
            options.extract_audio = True
            options.format_id = "bestaudio/best"
            fmt_map = {"MP3": "mp3", "M4A": "m4a", "FLAC": "flac", "WAV": "wav"}
            options.audio_format = fmt_map.get(self.audio_format_combo.currentText(), "mp3")
            options.audio_quality = self.audio_quality_combo.currentText().replace("k", "")
        elif mode_id == 1:
            codec_map = {"H.264": "h264", "H.265": "h265", "VP9": "vp9", "AV1": "av1"}
            if self._video_info:
                rec = self._ensure_strategy().recommend_format(
                    self._video_info,
                    self.quality_combo.currentText(),
                    codec_map.get(self.codec_combo.currentText(), "h264"),
                )
                options.format_id = rec.get("format_string", "bestvideo+bestaudio/best")
            else:
                options.format_id = "bestvideo+bestaudio/best"
            fmt_map = {"MP4": "mp4", "MKV": "mkv", "WebM": "webm"}
            options.merge_format = fmt_map.get(self.format_combo.currentText(), "mp4")
        else:
            options.format_id = "bestvideo+bestaudio/best"
            options.merge_format = "mp4"

        options.post_process_preset = self.post_process_combo.currentData() or "none"
        options.delete_source_after_post_process = self.delete_source_check.isChecked()
        return options

    def reset(self):
        self._video_info = None
        self.mode_best.setChecked(True)
        self.quality_combo.clear()
        self.size_label.setText("预计: -")
        self.transcode_label.setText("")
        self.post_process_combo.setCurrentIndex(0)
        self.delete_source_check.setChecked(False)
        self._update_post_process_ui()
        self._on_mode_changed()

    def apply_ui_metrics(self, metrics):
        self._format_layout.setContentsMargins(
            metrics.choose(8, 10, 12),
            metrics.choose(6, 8, 10),
            metrics.choose(8, 10, 12),
            metrics.choose(8, 10, 12),
        )
        self._format_layout.setSpacing(metrics.choose(6, 8, 10))
        self._mode_row.setSpacing(metrics.choose(6, 8, 10))
        self._custom_row.setSpacing(metrics.choose(8, 10, 12))
        self._audio_row.setSpacing(metrics.choose(8, 10, 12))
        self._post_row.setSpacing(metrics.choose(6, 8, 10))
        self._bottom_row.setSpacing(metrics.choose(8, 10, 12))

        combo_width = metrics.choose(84, 96, 112)
        self.quality_combo.setMinimumWidth(combo_width)
        self.codec_combo.setMinimumWidth(combo_width)
        self.format_combo.setMinimumWidth(combo_width)
        self.audio_format_combo.setMinimumWidth(combo_width)
        self.audio_quality_combo.setMinimumWidth(combo_width)
        self.download_btn.setFixedHeight(metrics.choose(36, 38, 40))
        self.download_btn.setFixedWidth(metrics.choose(154, 176, 188))
