"""
Progress widget for individual download tasks.
"""
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.download_task import DownloadTask, TaskStatus


class ProgressWidget(QWidget):
    """Widget displaying progress for a single download task."""

    pause_clicked = Signal(str)
    resume_clicked = Signal(str)
    cancel_clicked = Signal(str)
    retry_clicked = Signal(str)
    open_file_clicked = Signal(str)
    open_folder_clicked = Signal(str)

    def __init__(self, task: DownloadTask, parent=None):
        super().__init__(parent)
        self.task = task
        self._displayed_status = task.status
        self._status_tone = None
        self._eta_tone = None
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(125)
        self._update_timer.timeout.connect(self._flush_update)
        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        self.setMinimumHeight(78)
        self.setObjectName("progressCard")

        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(14, 10, 14, 10)
        self._main_layout.setSpacing(12)

        self.status_icon = QLabel("...")
        self.status_icon.setObjectName("statusIcon")
        self.status_icon.setFixedWidth(26)
        self._main_layout.addWidget(self.status_icon)

        self._info_layout = QVBoxLayout()
        self._info_layout.setSpacing(6)

        self._title_row = QHBoxLayout()
        self.title_label = QLabel(self.task.title or "未知标题")
        self.title_label.setObjectName("progressTitle")
        self.title_label.setMaximumWidth(400)
        self._title_row.addWidget(self.title_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")
        self._title_row.addWidget(self.status_label)
        self._title_row.addStretch()
        self._info_layout.addLayout(self._title_row)

        self._progress_row = QHBoxLayout()
        self._progress_row.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self._progress_row.addWidget(self.progress_bar, 1)

        self.percent_label = QLabel("0%")
        self.percent_label.setFixedWidth(40)
        self.percent_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._progress_row.addWidget(self.percent_label)

        self.speed_label = QLabel("")
        self.speed_label.setObjectName("status")
        self.speed_label.setFixedWidth(80)
        self._progress_row.addWidget(self.speed_label)

        self.eta_label = QLabel("")
        self.eta_label.setObjectName("muted")
        self.eta_label.setFixedWidth(120)
        self._progress_row.addWidget(self.eta_label)

        self._info_layout.addLayout(self._progress_row)
        self._main_layout.addLayout(self._info_layout, 1)

        self._button_layout = QHBoxLayout()
        self._button_layout.setSpacing(4)

        self.pause_btn = QPushButton("||")
        self.pause_btn.setObjectName("icon")
        self.pause_btn.setFixedSize(32, 32)
        self.pause_btn.setToolTip("暂停")
        self.pause_btn.clicked.connect(lambda: self.pause_clicked.emit(self.task.id))
        self._button_layout.addWidget(self.pause_btn)

        self.resume_btn = QPushButton(">")
        self.resume_btn.setObjectName("icon")
        self.resume_btn.setFixedSize(32, 32)
        self.resume_btn.setToolTip("继续")
        self.resume_btn.clicked.connect(lambda: self.resume_clicked.emit(self.task.id))
        self.resume_btn.setVisible(False)
        self._button_layout.addWidget(self.resume_btn)

        self.cancel_btn = QPushButton("X")
        self.cancel_btn.setObjectName("icon")
        self.cancel_btn.setFixedSize(32, 32)
        self.cancel_btn.setToolTip("取消")
        self.cancel_btn.clicked.connect(lambda: self.cancel_clicked.emit(self.task.id))
        self._button_layout.addWidget(self.cancel_btn)

        self.retry_btn = QPushButton("R")
        self.retry_btn.setObjectName("icon")
        self.retry_btn.setFixedSize(32, 32)
        self.retry_btn.setToolTip("重试")
        self.retry_btn.clicked.connect(lambda: self.retry_clicked.emit(self.task.id))
        self.retry_btn.setVisible(False)
        self._button_layout.addWidget(self.retry_btn)

        self.open_btn = QPushButton("F")
        self.open_btn.setObjectName("icon")
        self.open_btn.setFixedSize(32, 32)
        self.open_btn.setToolTip("打开所在文件夹")
        self.open_btn.clicked.connect(lambda: self.open_folder_clicked.emit(self.task.id))
        self.open_btn.setVisible(False)
        self._button_layout.addWidget(self.open_btn)

        self._main_layout.addLayout(self._button_layout)

    def update_task(self, task: DownloadTask):
        self.task = task
        if task.status != self._displayed_status or not task.is_active:
            if self._update_timer.isActive():
                self._update_timer.stop()
            self._flush_update()
            return
        if not self._update_timer.isActive():
            self._update_timer.start()

    def apply_task(self, task: DownloadTask):
        self.task = task
        if self._update_timer.isActive():
            self._update_timer.stop()
        self._flush_update()

    @property
    def displayed_status(self):
        return self._displayed_status

    def _flush_update(self):
        self._update_display()

    def _update_display(self):
        task = self.task
        self._displayed_status = task.status

        title = task.title or "未知标题"
        if len(title) > 50:
            title = title[:47] + "..."
        self._set_label_text(self.title_label, title)

        status_icons = {
            TaskStatus.PENDING: ("...", "muted"),
            TaskStatus.PARSING: ("P", "status"),
            TaskStatus.DOWNLOADING: ("D", "status"),
            TaskStatus.PROCESSING: ("W", "warning"),
            TaskStatus.PAUSED: ("II", "warning"),
            TaskStatus.COMPLETED: ("OK", "success"),
            TaskStatus.FAILED: ("!", "error"),
            TaskStatus.CANCELLED: ("X", "muted"),
        }

        icon, tone = status_icons.get(task.status, ("...", "muted"))
        self._set_label_text(self.status_icon, icon)
        self._set_label_text(self.status_label, task.status_text)
        self._set_tone(self.status_label, tone, "_status_tone")

        if task.status == TaskStatus.COMPLETED:
            self._set_progress_value(100)
            self._set_label_text(self.percent_label, "100%")
            self._set_label_text(self.speed_label, "")
            self._set_label_text(self.eta_label, "")
        elif task.status in (TaskStatus.DOWNLOADING, TaskStatus.PROCESSING):
            percent = int(task.progress.percent)
            self._set_progress_value(percent)
            self._set_label_text(self.percent_label, f"{percent}%")
            self._set_label_text(self.speed_label, task.progress.speed_str)
            self._set_label_text(self.eta_label, task.progress.eta_str)
        else:
            self._set_progress_value(0)
            self._set_label_text(self.percent_label, "0%")
            self._set_label_text(self.speed_label, "")
            self._set_label_text(self.eta_label, "")

        if task.status == TaskStatus.FAILED and task.error_message:
            error = task.error_message[:40] + "..." if len(task.error_message) > 40 else task.error_message
            self._set_label_text(self.eta_label, error)
            self._set_tone(self.eta_label, "error", "_eta_tone")
        else:
            self._set_tone(self.eta_label, "muted", "_eta_tone")

        is_active = task.status in (
            TaskStatus.DOWNLOADING,
            TaskStatus.PARSING,
            TaskStatus.PROCESSING,
        )
        is_paused = task.status == TaskStatus.PAUSED
        is_failed = task.status == TaskStatus.FAILED
        is_completed = task.status == TaskStatus.COMPLETED
        is_pending = task.status == TaskStatus.PENDING
        has_output = bool(task.output_file)

        self._set_button_visible(self.pause_btn, is_active or is_pending)
        self._set_button_visible(self.resume_btn, is_paused)
        self._set_button_visible(
            self.cancel_btn,
            not is_completed and task.status != TaskStatus.CANCELLED,
        )
        self._set_button_visible(self.retry_btn, is_failed)
        self._set_button_visible(
            self.open_btn,
            has_output
            and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED),
        )

    def _refresh_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _set_tone(self, widget, tone, attr_name):
        if getattr(self, attr_name) == tone:
            return
        setattr(self, attr_name, tone)
        widget.setObjectName(tone)
        self._refresh_style(widget)

    @staticmethod
    def _set_label_text(widget, text):
        if widget.text() == text:
            return
        widget.setText(text)

    def _set_progress_value(self, value):
        if self.progress_bar.value() == value:
            return
        self.progress_bar.setValue(value)

    @staticmethod
    def _set_button_visible(widget, visible):
        if widget.isHidden() == (not visible):
            return
        widget.setVisible(visible)

    def apply_ui_metrics(self, metrics):
        self.setMinimumHeight(metrics.choose(70, 78, 84))
        self._main_layout.setContentsMargins(
            metrics.choose(10, 14, 16),
            metrics.choose(8, 10, 12),
            metrics.choose(10, 14, 16),
            metrics.choose(8, 10, 12),
        )
        self._main_layout.setSpacing(metrics.choose(8, 12, 14))
        self._info_layout.setSpacing(metrics.choose(4, 6, 8))
        self._progress_row.setSpacing(metrics.choose(6, 8, 10))
        self._button_layout.setSpacing(metrics.choose(3, 4, 5))

        self.status_icon.setFixedWidth(metrics.choose(22, 26, 28))
        self.title_label.setMaximumWidth(metrics.choose(260, 400, 520))
        self.progress_bar.setFixedHeight(metrics.choose(5, 6, 7))
        self.percent_label.setFixedWidth(metrics.choose(36, 40, 44))
        self.speed_label.setFixedWidth(metrics.choose(68, 80, 88))
        self.eta_label.setFixedWidth(metrics.choose(96, 120, 136))

        icon_size = metrics.choose(28, 32, 34)
        for button in (
            self.pause_btn,
            self.resume_btn,
            self.cancel_btn,
            self.retry_btn,
            self.open_btn,
        ):
            button.setFixedSize(icon_size, icon_size)
