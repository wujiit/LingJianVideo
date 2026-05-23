"""
Video compressor widget.
"""
import os

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.ffmpeg_processor import FFmpegProcessor
from core.media_presets import COMPRESSION_PRESETS, build_output_path


SCALE_TO_LABEL = {
    1.0: "保持原始分辨率",
    0.75: "75%（轻微缩小）",
    0.5: "50%（推荐，明显减小）",
    0.25: "25%（极小尺寸）",
}

LABEL_TO_SCALE = {label: value for value, label in SCALE_TO_LABEL.items()}


class CompressWorker(QThread):
    progress = Signal(float)
    finished = Signal(bool, str)
    log_message = Signal(str)

    def __init__(self, processor, input_path, output_path, options):
        super().__init__()
        self.processor = processor
        self.input_path = input_path
        self.output_path = output_path
        self.options = options
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        self.processor.cancel()

    def _log_callback(self, msg):
        self.log_message.emit(msg)

    def run(self):
        try:
            self.log_message.emit("开始压缩任务")
            self.log_message.emit(f"输入: {self.input_path}")
            self.log_message.emit(f"输出: {self.output_path}")

            if not os.path.exists(self.input_path):
                self.finished.emit(False, "输入文件不存在")
                return

            success = self.processor.compress_video(
                self.input_path,
                self.output_path,
                target_size_mb=self.options.get("target_size"),
                crf=self.options.get("crf"),
                preset=self.options.get("preset", "medium"),
                width_scale=self.options.get("width_scale"),
                progress_callback=self.progress.emit,
                log_callback=self._log_callback,
            )

            if self._cancelled:
                self.finished.emit(False, "操作已取消")
            elif success:
                self.finished.emit(True, "压缩完成")
            else:
                self.finished.emit(False, "压缩失败，请查看日志")
        except Exception as exc:
            import traceback

            self.log_message.emit(f"发生异常: {exc}\n{traceback.format_exc()}")
            self.finished.emit(False, str(exc))


class CompressorWidget(QWidget):
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
        self.input_path.setPlaceholderText("请选择要压缩的视频文件...")
        self.input_path.setReadOnly(True)
        self.input_path.setFixedHeight(40)

        self._browse_btn = QPushButton("浏览...")
        self._browse_btn.setFixedSize(110, 40)
        self._browse_btn.clicked.connect(self._browse_file)

        self._file_row.addWidget(self.input_path, 1)
        self._file_row.addWidget(self._browse_btn, 0)
        self._file_layout.addLayout(self._file_row)

        self.file_info_label = QLabel("")
        self.file_info_label.setObjectName("muted")
        self.file_info_label.setWordWrap(True)
        self._file_layout.addWidget(self.file_info_label)
        self._root_layout.addWidget(self._file_group)

        self._settings_group = QGroupBox("压缩设置")
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
        self.preset_combo = self._make_combo(220)
        self.preset_combo.addItem("自定义", "custom")
        for key, preset in COMPRESSION_PRESETS.items():
            self.preset_combo.addItem(preset["label"], key)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.preset_combo.setToolTip("选择常用压缩模板，或保持自定义。")

        self.radio_size = QRadioButton("按目标大小")
        self.radio_quality = QRadioButton("按画质 (CRF)")
        self.radio_quality.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_size)
        self.mode_group.addButton(self.radio_quality)
        self.mode_group.buttonClicked.connect(self._update_mode_ui)

        self._mode_widget = QWidget()
        self._mode_row = QHBoxLayout(self._mode_widget)
        self._mode_row.setContentsMargins(0, 0, 0, 0)
        self._mode_row.setSpacing(8)
        self._mode_row.addWidget(self.radio_size, 0)
        self._mode_row.addWidget(self.radio_quality, 0)
        self._mode_row.addStretch(1)

        self.res_combo = self._make_combo(220)
        self.res_combo.addItems(list(SCALE_TO_LABEL.values()))

        self.mode_stack = QStackedWidget()
        self.mode_stack.setFixedHeight(44)
        self.mode_stack.setMinimumWidth(280)
        self.mode_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mode_stack.addWidget(self._build_size_page())
        self.mode_stack.addWidget(self._build_quality_page())

        preset_label = self._make_label("模板:")
        mode_label = self._make_label("压缩模式:")
        resolution_label = self._make_label("分辨率:")
        params_label = self._make_label("参数:")
        self._settings_labels.extend(
            [preset_label, mode_label, resolution_label, params_label]
        )

        self._settings_grid.addWidget(preset_label, 0, 0)
        self._settings_grid.addWidget(self.preset_combo, 0, 1)
        self._settings_grid.addWidget(mode_label, 0, 2)
        self._settings_grid.addWidget(self._mode_widget, 0, 3)
        self._settings_grid.addWidget(resolution_label, 1, 0)
        self._settings_grid.addWidget(self.res_combo, 1, 1)
        self._settings_grid.addWidget(params_label, 1, 2)
        self._settings_grid.addWidget(self.mode_stack, 1, 3)

        self._settings_layout.addLayout(self._settings_grid)
        self._root_layout.addWidget(self._settings_group)

        self._update_mode_ui()
        self._on_quality_changed(self.quality_combo.currentIndex())

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
        self.log_output.setPlaceholderText("压缩日志将显示在这里...")
        self.log_output.setMinimumHeight(120)
        self.log_output.setMaximumHeight(160)
        self.log_output.setReadOnly(True)
        self._progress_layout.addWidget(self.log_output)
        self._root_layout.addWidget(self._progress_group, 1)

        self._button_row = QHBoxLayout()
        self._button_row.setContentsMargins(0, 0, 0, 0)
        self._button_row.addStretch(1)

        self.btn_start = QPushButton("开始压缩")
        self.btn_start.setObjectName("primary")
        self.btn_start.setMinimumWidth(140)
        self.btn_start.setFixedHeight(42)
        self.btn_start.clicked.connect(self._start_compression)
        self._button_row.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setMinimumWidth(110)
        self.btn_cancel.setFixedHeight(42)
        self.btn_cancel.clicked.connect(self._cancel_compression)
        self.btn_cancel.setEnabled(False)
        self._button_row.addWidget(self.btn_cancel)
        self._root_layout.addLayout(self._button_row)

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

    def _build_size_page(self):
        page = QWidget()
        self._size_row = QHBoxLayout(page)
        self._size_row.setContentsMargins(0, 0, 0, 0)
        self._size_row.setSpacing(8)

        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(1, 10000)
        self.size_spin.setValue(50)
        self.size_spin.setSuffix(" MB")
        self.size_spin.setMinimumWidth(170)
        self.size_spin.setFixedHeight(40)
        self.size_spin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._size_row.addWidget(self.size_spin, 1)

        return page

    def _build_quality_page(self):
        page = QWidget()
        self._quality_row = QHBoxLayout(page)
        self._quality_row.setContentsMargins(0, 0, 0, 0)
        self._quality_row.setSpacing(8)

        self.quality_combo = QComboBox()
        self.quality_combo.setFixedHeight(40)
        self.quality_combo.setMinimumWidth(190)
        self.quality_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.quality_combo.addItems(
            [
                "高画质 (CRF 18)",
                "推荐 (CRF 23)",
                "中等 (CRF 28)",
                "低画质 (CRF 32)",
                "自定义",
            ]
        )
        self.quality_combo.setCurrentText("推荐 (CRF 23)")
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        self._quality_row.addWidget(self.quality_combo, 1)

        self.crf_spin = QDoubleSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(23)
        self.crf_spin.setDecimals(0)
        self.crf_spin.setPrefix("CRF ")
        self.crf_spin.setMinimumWidth(100)
        self.crf_spin.setFixedHeight(40)
        self._quality_row.addWidget(self.crf_spin, 0)

        return page

    def _update_mode_ui(self, *_args):
        is_size = self.radio_size.isChecked()
        self.mode_stack.setCurrentIndex(0 if is_size else 1)
        if is_size:
            self.radio_size.setToolTip("适合上传体积受限场景。")
            self.radio_quality.setToolTip("")
        else:
            self.radio_quality.setToolTip("适合大多数本地压缩场景。")
            self.radio_size.setToolTip("")

    def _on_quality_changed(self, index):
        del index
        self.crf_spin.setVisible(self.quality_combo.currentText() == "自定义")

    def _on_preset_changed(self, *_args):
        preset_key = self.preset_combo.currentData()
        if preset_key == "custom":
            self.preset_combo.setToolTip("手动设置压缩模式、分辨率和参数。")
            return

        preset = COMPRESSION_PRESETS.get(preset_key)
        if not preset:
            return

        self.preset_combo.setToolTip(preset.get("description", ""))
        scale_label = SCALE_TO_LABEL.get(
            preset.get("width_scale", 1.0), SCALE_TO_LABEL[1.0]
        )
        self._set_combo_by_text(self.res_combo, scale_label)

        if preset.get("mode") == "target_size":
            self.radio_size.setChecked(True)
            self.size_spin.setValue(float(preset.get("target_size", 50.0)))
        else:
            self.radio_quality.setChecked(True)
            crf = int(preset.get("crf", 23))
            if crf == 18:
                self._set_combo_by_text(self.quality_combo, "高画质 (CRF 18)")
            elif crf == 23:
                self._set_combo_by_text(self.quality_combo, "推荐 (CRF 23)")
            elif crf == 28:
                self._set_combo_by_text(self.quality_combo, "中等 (CRF 28)")
            elif crf == 32:
                self._set_combo_by_text(self.quality_combo, "低画质 (CRF 32)")
            else:
                self._set_combo_by_text(self.quality_combo, "自定义")
                self.crf_spin.setValue(crf)

        self._update_mode_ui()
        self._on_quality_changed(self.quality_combo.currentIndex())

    @staticmethod
    def _set_combo_by_text(combo, text):
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv);;所有文件 (*.*)",
        )
        if path:
            self.input_path.setText(path)
            self._update_file_info(path)

    def _update_file_info(self, path):
        if not os.path.exists(path):
            return

        info = self._processor.get_media_info(path)
        if info:
            size_mb = info.file_size / (1024 * 1024)
            self.file_info_label.setText(
                f"原始大小: {size_mb:.2f} MB | 时长: {info.duration:.1f}s | 分辨率: {info.width}x{info.height}"
            )
            self.size_spin.setValue(max(1.0, size_mb * 0.5))

    def _build_options(self):
        options = {
            "preset": "medium",
            "width_scale": LABEL_TO_SCALE.get(self.res_combo.currentText(), 1.0),
        }

        preset_key = self.preset_combo.currentData()
        if preset_key != "custom":
            preset = COMPRESSION_PRESETS.get(preset_key, {})
            options["preset"] = preset.get("preset", "medium")

        if self.radio_size.isChecked():
            options["target_size"] = self.size_spin.value()
        else:
            quality_text = self.quality_combo.currentText()
            if quality_text == "自定义":
                options["crf"] = int(self.crf_spin.value())
            elif "高画质" in quality_text:
                options["crf"] = 18
            elif "推荐" in quality_text:
                options["crf"] = 23
            elif "中等" in quality_text:
                options["crf"] = 28
            elif "低画质" in quality_text:
                options["crf"] = 32

        return options

    def _start_compression(self):
        input_file = self.input_path.text()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "错误", "请先选择有效的视频文件")
            return

        ext = os.path.splitext(input_file)[1].lstrip(".") or "mp4"
        output_file = build_output_path(input_file, "compressed", ext)

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在压缩...")
        self.log_output.clear()

        options = self._build_options()
        self._worker = CompressWorker(
            self._processor, input_file, output_file, options
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

    def _cancel_compression(self):
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
        self._mode_row.setSpacing(metrics.choose(6, 8, 10))
        self._size_row.setSpacing(metrics.choose(6, 8, 10))
        self._quality_row.setSpacing(metrics.choose(6, 8, 10))
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
        self.preset_combo.setMinimumWidth(metrics.choose(180, 220, 240))
        self.preset_combo.setFixedHeight(metrics.choose(36, 40, 42))
        self.res_combo.setMinimumWidth(metrics.choose(180, 220, 240))
        self.res_combo.setFixedHeight(metrics.choose(36, 40, 42))
        self.mode_stack.setMinimumWidth(metrics.choose(220, 280, 320))
        self.mode_stack.setFixedHeight(metrics.choose(40, 44, 46))
        self.size_spin.setMinimumWidth(metrics.choose(140, 170, 190))
        self.size_spin.setFixedHeight(metrics.choose(36, 40, 42))
        self.quality_combo.setMinimumWidth(metrics.choose(150, 190, 220))
        self.quality_combo.setFixedHeight(metrics.choose(36, 40, 42))
        self.crf_spin.setMinimumWidth(metrics.choose(88, 100, 110))
        self.crf_spin.setFixedHeight(metrics.choose(36, 40, 42))
        self.log_output.setMinimumHeight(metrics.choose(104, 120, 140))
        self.log_output.setMaximumHeight(metrics.choose(144, 160, 184))
        self.btn_start.setMinimumWidth(metrics.choose(118, 140, 148))
        self.btn_start.setFixedHeight(metrics.choose(38, 42, 44))
        self.btn_cancel.setMinimumWidth(metrics.choose(92, 110, 118))
        self.btn_cancel.setFixedHeight(metrics.choose(38, 42, 44))

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
