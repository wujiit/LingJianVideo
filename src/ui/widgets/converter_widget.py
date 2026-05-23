"""
Video/audio converter widget.
"""
import os
import re

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.ffmpeg_processor import FFmpegProcessor
from core.media_presets import CONVERSION_PRESETS, build_output_path


VIDEO_QUALITY_TO_PRESET = {
    "最佳画质": ("veryslow", 18),
    "高画质": ("slow", 20),
    "平衡": ("medium", 23),
    "快速": ("veryfast", 25),
    "极速": ("ultrafast", 28),
}

TIME_INPUT_RE = re.compile(r"^\d+(?::\d{1,2}){0,2}(?:\.\d+)?$")


class ConvertWorker(QThread):
    progress = Signal(float)
    finished = Signal(bool, str)
    log_message = Signal(str)

    def __init__(self, processor, input_path, output_path, options, mode="convert"):
        super().__init__()
        self.processor = processor
        self.input_path = input_path
        self.output_path = output_path
        self.options = options
        self.mode = mode
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        self.processor.cancel()

    def _log_callback(self, msg):
        self.log_message.emit(msg)

    def run(self):
        try:
            self.log_message.emit(f"开始任务: {self.mode}")
            self.log_message.emit(f"输入: {self.input_path}")
            self.log_message.emit(f"输出: {self.output_path}")

            if not os.path.exists(self.input_path):
                self.finished.emit(False, "输入文件不存在")
                return

            if self.mode == "extract_audio":
                success = self.processor.extract_audio(
                    self.input_path,
                    self.output_path,
                    audio_format=self.options.get("format", "mp3"),
                    audio_quality=self.options.get("quality", "192"),
                    clip_start=self.options.get("clip_start", ""),
                    clip_end=self.options.get("clip_end", ""),
                    progress_callback=self.progress.emit,
                    log_callback=self._log_callback,
                )
            else:
                success = self.processor.convert_format(
                    self.input_path,
                    self.output_path,
                    self.options,
                    progress_callback=self.progress.emit,
                    log_callback=self._log_callback,
                )

            if self._cancelled:
                self.finished.emit(False, "操作已取消")
            elif success:
                self.finished.emit(True, "转换完成")
            else:
                self.finished.emit(False, "转换失败，请查看日志")
        except Exception as exc:
            import traceback

            self.log_message.emit(f"发生异常: {exc}\n{traceback.format_exc()}")
            self.finished.emit(False, str(exc))


class ConverterWidget(QWidget):
    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self._config = config_manager
        self._processor = FFmpegProcessor(
            self._config.get_ffmpeg_path() if self._config else None
        )
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setSpacing(4)
        self._root_layout.setContentsMargins(0, 0, 0, 0)

        self._file_group = QGroupBox("文件选择")
        self._file_group.setObjectName("panelCard")
        self._file_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._file_layout = QVBoxLayout(self._file_group)
        self._file_layout.setContentsMargins(4, 4, 4, 4)
        self._file_layout.setSpacing(4)

        self._file_row = QHBoxLayout()
        self._file_row.setContentsMargins(0, 0, 0, 0)
        self._file_row.setSpacing(8)
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("请选择要转换的视频或音频文件...")
        self.input_path.setReadOnly(True)
        self.input_path.setFixedHeight(40)

        self._browse_btn = QPushButton("浏览...")
        self._browse_btn.setFixedSize(110, 40)
        self._browse_btn.clicked.connect(self._browse_file)

        self._file_row.addWidget(self.input_path, 1)
        self._file_row.addWidget(self._browse_btn, 0)
        self._file_layout.addLayout(self._file_row)
        self._root_layout.addWidget(self._file_group)

        self._settings_group = QGroupBox("转换设置")
        self._settings_group.setObjectName("panelCard")
        self._settings_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._settings_layout = QVBoxLayout(self._settings_group)
        self._settings_layout.setContentsMargins(4, 4, 4, 4)
        self._settings_layout.setSpacing(4)

        self._settings_grid = QGridLayout()
        self._settings_grid.setContentsMargins(0, 0, 0, 0)
        self._settings_grid.setHorizontalSpacing(8)
        self._settings_grid.setVerticalSpacing(6)
        self._settings_grid.setColumnStretch(1, 3)
        self._settings_grid.setColumnStretch(3, 4)

        self._settings_labels = []
        self.template_combo = self._make_combo(220)
        self.template_combo.addItem("自定义", "custom")
        for key, preset in CONVERSION_PRESETS.items():
            self.template_combo.addItem(preset["label"], key)
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self.template_combo.setToolTip("选择常用转换模板，或保持自定义。")

        self.format_combo = self._make_combo(220)
        self.format_combo.addItem("MP3 (音频)", "mp3")
        self.format_combo.addItem("M4A (音频)", "m4a")
        self.format_combo.addItem("WAV (音频)", "wav")
        self.format_combo.addItem("FLAC (音频)", "flac")
        self.format_combo.addItem("MP4 (视频)", "mp4")
        self.format_combo.addItem("MKV (视频)", "mkv")
        self.format_combo.addItem("AVI (视频)", "avi")
        self.format_combo.addItem("MOV (视频)", "mov")
        self.format_combo.currentTextChanged.connect(self._on_format_changed)

        self.quality_combo = self._make_combo(180)

        template_label = self._make_label("模板:")
        format_label = self._make_label("目标格式:")
        quality_label = self._make_label("质量/速度:")
        self._settings_labels.extend([template_label, format_label, quality_label])

        self._settings_grid.addWidget(template_label, 0, 0)
        self._settings_grid.addWidget(self.template_combo, 0, 1)
        self._settings_grid.addWidget(format_label, 0, 2)
        self._settings_grid.addWidget(self.format_combo, 0, 3)
        self._settings_grid.addWidget(quality_label, 1, 0)
        self._settings_grid.addWidget(self.quality_combo, 1, 1)

        self._options_widget = QWidget()
        self._options_row = QHBoxLayout(self._options_widget)
        self._options_row.setContentsMargins(0, 0, 0, 0)
        self._options_row.setSpacing(8)

        self.quick_copy_check = QCheckBox("优先快速转换")
        self.quick_copy_check.setChecked(True)
        self.quick_copy_check.setToolTip("能直接封装时不重新编码，速度更快。")

        self.clip_toggle = QCheckBox("剪辑片段")
        self.clip_toggle.toggled.connect(self._toggle_clip_fields)

        self.clip_fields_widget = QWidget()
        self.clip_fields_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self._clip_row = QHBoxLayout(self.clip_fields_widget)
        self._clip_row.setContentsMargins(0, 0, 0, 0)
        self._clip_row.setSpacing(8)

        self._clip_start_label = QLabel("开始")
        self._clip_end_label = QLabel("结束")
        self._clip_row.addWidget(self._clip_start_label, 0)

        self.clip_start_edit = self._make_line_edit("如 00:01:30", 150)
        self.clip_start_edit.setToolTip("支持 90 / 01:30 / 00:01:30")
        self._clip_row.addWidget(self.clip_start_edit, 1)

        self._clip_row.addWidget(self._clip_end_label, 0)
        self.clip_end_edit = self._make_line_edit("如 00:03:00", 150)
        self.clip_end_edit.setToolTip("支持 90 / 01:30 / 00:01:30")
        self._clip_row.addWidget(self.clip_end_edit, 1)

        self.clip_fields_widget.setVisible(False)

        self._options_row.addWidget(self.quick_copy_check, 0)
        self._options_row.addWidget(self.clip_toggle, 0)
        self._options_row.addWidget(self.clip_fields_widget, 1)
        self._options_row.addStretch(1)
        self._settings_grid.addWidget(self._options_widget, 1, 2, 1, 2)

        self._settings_layout.addLayout(self._settings_grid)
        self._root_layout.addWidget(self._settings_group)

        self._progress_group = QGroupBox("进度")
        self._progress_group.setObjectName("panelCard")
        self._progress_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._progress_layout = QVBoxLayout(self._progress_group)
        self._progress_layout.setContentsMargins(4, 4, 4, 4)
        self._progress_layout.setSpacing(4)

        self.status_label = QLabel("准备就绪")
        self._progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self._progress_layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setPlaceholderText("转换日志将显示在这里...")
        self.log_output.setMinimumHeight(110)
        self.log_output.setMaximumHeight(150)
        self.log_output.setReadOnly(True)
        self._progress_layout.addWidget(self.log_output)
        self._root_layout.addWidget(self._progress_group, 1)

        self._button_row = QHBoxLayout()
        self._button_row.setContentsMargins(0, 0, 0, 0)
        self._button_row.addStretch(1)

        self.btn_start = QPushButton("开始转换")
        self.btn_start.setObjectName("primary")
        self.btn_start.setFixedSize(140, 40)
        self.btn_start.clicked.connect(self._start_conversion)
        self._button_row.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFixedSize(110, 40)
        self.btn_cancel.clicked.connect(self._cancel_conversion)
        self.btn_cancel.setEnabled(False)
        self._button_row.addWidget(self.btn_cancel)
        self._root_layout.addLayout(self._button_row)

        self._on_format_changed(self.format_combo.currentText())

    @staticmethod
    def _make_label(text):
        label = QLabel(text)
        label.setFixedWidth(60)
        return label

    @staticmethod
    def _make_combo(minimum_width=0):
        combo = QComboBox()
        combo.setFixedHeight(40)
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if minimum_width:
            combo.setMinimumWidth(minimum_width)
        return combo

    @staticmethod
    def _make_line_edit(placeholder, minimum_width):
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setMinimumWidth(minimum_width)
        line_edit.setFixedHeight(36)
        line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return line_edit

    def _toggle_clip_fields(self, enabled):
        self.clip_fields_widget.setVisible(enabled)
        if not enabled:
            self.clip_start_edit.clear()
            self.clip_end_edit.clear()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文件",
            "",
            "媒体文件 (*.mp4 *.mkv *.avi *.mov *.mp3 *.m4a *.wav *.flac);;所有文件 (*.*)",
        )
        if path:
            self.input_path.setText(path)
            self.status_label.setText("已选择文件")

    def _on_format_changed(self, text):
        self.quality_combo.clear()
        is_audio = "音频" in text

        if is_audio:
            self.quality_combo.addItems(["320k", "256k", "192k", "128k"])
            self.quality_combo.setCurrentText("192k")
            self.quick_copy_check.setChecked(False)
            self.quick_copy_check.setEnabled(False)
            self.quick_copy_check.setVisible(False)
        else:
            self.quality_combo.addItems(list(VIDEO_QUALITY_TO_PRESET.keys()))
            self.quality_combo.setCurrentText("平衡")
            self.quick_copy_check.setEnabled(True)
            self.quick_copy_check.setVisible(True)

    def _on_template_changed(self, *_args):
        preset_key = self.template_combo.currentData()
        if preset_key == "custom":
            self.template_combo.setToolTip("手动选择格式、速度和剪辑时间。")
            return

        preset = CONVERSION_PRESETS.get(preset_key)
        if not preset:
            return

        self.template_combo.setToolTip(preset.get("description", ""))
        target_format = preset.get("target_format", "mp4").lower()
        self._set_combo_by_data(self.format_combo, target_format)

        if preset["mode"] == "audio":
            self._set_combo_by_text(
                self.quality_combo, preset.get("audio_quality", "192k")
            )
        else:
            self._set_combo_by_text(
                self.quality_combo, preset.get("quality_label", "平衡")
            )
            self.quick_copy_check.setChecked(bool(preset.get("quick_copy", False)))

    @staticmethod
    def _set_combo_by_text(combo, text):
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _set_combo_by_data(combo, data):
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _parse_time_value(value):
        if not value:
            return None
        parts = [float(part) for part in value.split(":")]
        total = 0.0
        for part in parts:
            total = total * 60 + part
        return total

    def _validate_clip_inputs(self):
        if not self.clip_toggle.isChecked():
            return "", ""

        clip_start = self.clip_start_edit.text().strip()
        clip_end = self.clip_end_edit.text().strip()

        for label, value in (("开始时间", clip_start), ("结束时间", clip_end)):
            if value and not TIME_INPUT_RE.match(value):
                QMessageBox.warning(
                    self, "时间格式错误", f"{label}格式无效：{value}"
                )
                return None, None

        start_seconds = self._parse_time_value(clip_start)
        end_seconds = self._parse_time_value(clip_end)
        if (
            start_seconds is not None
            and end_seconds is not None
            and end_seconds <= start_seconds
        ):
            QMessageBox.warning(self, "时间范围错误", "结束时间必须大于开始时间")
            return None, None

        return clip_start, clip_end

    def _build_output_path(self, input_file, target_ext, has_clip, quick_copy):
        if has_clip:
            suffix = "clip"
        elif quick_copy:
            suffix = "quick"
        else:
            suffix = "converted"
        return build_output_path(input_file, suffix, target_ext)

    def _start_conversion(self):
        input_file = self.input_path.text()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "错误", "请先选择有效的文件")
            return

        clip_start, clip_end = self._validate_clip_inputs()
        if clip_start is None and clip_end is None:
            return

        target_ext = self.format_combo.currentData()
        target_text = self.format_combo.currentText()
        is_audio = "音频" in target_text
        quick_copy = self.quick_copy_check.isChecked() and not is_audio
        output_file = self._build_output_path(
            input_file,
            target_ext,
            bool(clip_start or clip_end),
            quick_copy,
        )

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在转换...")
        self.log_output.clear()

        options = {
            "clip_start": clip_start,
            "clip_end": clip_end,
        }
        mode = "convert"

        if is_audio:
            mode = "extract_audio"
            options["format"] = target_ext
            options["quality"] = self.quality_combo.currentText().replace("k", "")
        else:
            preset_name, crf = VIDEO_QUALITY_TO_PRESET.get(
                self.quality_combo.currentText(),
                ("medium", 23),
            )
            options.update(
                {
                    "target_ext": target_ext,
                    "quick_copy": quick_copy,
                    "preset": preset_name,
                    "vcodec": "libx264",
                    "acodec": "aac",
                    "crf": crf,
                }
            )

        self._worker = ConvertWorker(
            self._processor, input_file, output_file, options, mode
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.log_message.connect(self._append_log)
        self._worker.start()

    def _on_progress(self, value):
        self.progress_bar.setValue(int(value))

    def _append_log(self, msg):
        self.log_output.append(msg)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _cancel_conversion(self):
        if self._worker:
            self._worker.cancel()
            self.status_label.setText("正在取消...")

    def _on_finished(self, success, message):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.status_label.setText(message)
        self._worker = None
        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "完成", message)
        elif "取消" not in message:
            QMessageBox.critical(self, "错误", message)

    def apply_ui_metrics(self, metrics):
        self._root_layout.setSpacing(metrics.choose(2, 4, 6))
        self._file_layout.setContentsMargins(
            metrics.choose(2, 4, 6),
            metrics.choose(2, 4, 6),
            metrics.choose(2, 4, 6),
            metrics.choose(2, 4, 6),
        )
        self._file_layout.setSpacing(metrics.choose(2, 4, 6))
        self._file_row.setSpacing(metrics.choose(4, 6, 8))
        self._settings_layout.setContentsMargins(
            metrics.choose(2, 4, 6),
            metrics.choose(2, 4, 6),
            metrics.choose(2, 4, 6),
            metrics.choose(2, 4, 6),
        )
        self._settings_layout.setSpacing(metrics.choose(2, 4, 6))
        self._settings_grid.setHorizontalSpacing(metrics.choose(6, 8, 10))
        self._settings_grid.setVerticalSpacing(metrics.choose(4, 6, 8))
        self._options_row.setSpacing(metrics.choose(6, 8, 10))
        self._clip_row.setSpacing(metrics.choose(6, 8, 10))
        self._progress_layout.setContentsMargins(
            metrics.choose(2, 4, 6),
            metrics.choose(2, 4, 6),
            metrics.choose(2, 4, 6),
            metrics.choose(2, 4, 6),
        )
        self._progress_layout.setSpacing(metrics.choose(2, 4, 6))

        label_width = metrics.choose(50, 60, 66)
        for label in self._settings_labels:
            label.setFixedWidth(label_width)

        self.input_path.setFixedHeight(metrics.choose(36, 40, 42))
        self._browse_btn.setFixedSize(
            metrics.choose(96, 110, 120), metrics.choose(36, 40, 42)
        )
        self.template_combo.setMinimumWidth(metrics.choose(180, 220, 240))
        self.template_combo.setFixedHeight(metrics.choose(36, 40, 42))
        self.format_combo.setMinimumWidth(metrics.choose(180, 220, 240))
        self.format_combo.setFixedHeight(metrics.choose(36, 40, 42))
        self.quality_combo.setMinimumWidth(metrics.choose(140, 180, 200))
        self.quality_combo.setFixedHeight(metrics.choose(36, 40, 42))
        self.clip_start_edit.setMinimumWidth(metrics.choose(120, 150, 170))
        self.clip_start_edit.setFixedHeight(metrics.choose(34, 36, 38))
        self.clip_end_edit.setMinimumWidth(metrics.choose(120, 150, 170))
        self.clip_end_edit.setFixedHeight(metrics.choose(34, 36, 38))
        self.log_output.setMinimumHeight(metrics.choose(96, 110, 124))
        self.log_output.setMaximumHeight(metrics.choose(132, 150, 180))
        self.btn_start.setFixedSize(
            metrics.choose(118, 140, 148), metrics.choose(36, 40, 42)
        )
        self.btn_cancel.setFixedSize(
            metrics.choose(92, 110, 118), metrics.choose(36, 40, 42)
        )

    def shutdown(self, timeout_ms: int = 1500):
        if self._worker is None:
            if hasattr(self._processor, "shutdown"):
                self._processor.shutdown(timeout_ms)
            return

        worker = self._worker
        self._worker = None
        worker.cancel()
        if hasattr(self._processor, "shutdown"):
            self._processor.shutdown(timeout_ms)
        if worker.isRunning():
            worker.wait(timeout_ms)
        if worker.isRunning():
            worker.terminate()
            worker.wait(500)
