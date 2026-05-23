"""
Queue widget for managing download tasks.
"""
from typing import Dict

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.download_task import DownloadTask, TaskStatus
from ui.widgets.progress_widget import ProgressWidget


class QueueWidget(QWidget):
    """Widget for displaying and managing download queue."""

    pause_task = Signal(str)
    resume_task = Signal(str)
    cancel_task = Signal(str)
    retry_task = Signal(str)
    clear_completed = Signal()
    open_file = Signal(str)
    open_folder = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._task_widgets: Dict[str, ProgressWidget] = {}
        self._pending_updates: Dict[str, DownloadTask] = {}
        self._bulk_update_depth = 0
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(90)
        self._flush_timer.timeout.connect(self._flush_pending_updates)
        self._metrics = None
        self._setup_ui()

    def _setup_ui(self):
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        self._queue_group = QGroupBox("下载队列")
        self._queue_group.setObjectName("panelCard")
        self._queue_layout = QVBoxLayout(self._queue_group)
        self._queue_layout.setContentsMargins(12, 10, 12, 12)
        self._queue_layout.setSpacing(8)

        self._header_layout = QHBoxLayout()
        self._header_layout.setSpacing(8)

        self.count_label = QLabel("(0)")
        self.count_label.setObjectName("muted")
        self._header_layout.addWidget(self.count_label)
        self._header_layout.addStretch()

        self.clear_btn = QPushButton("清除已完成")
        self.clear_btn.setObjectName("ghost")
        self.clear_btn.setFixedHeight(32)
        self.clear_btn.clicked.connect(self.clear_completed.emit)
        self._header_layout.addWidget(self.clear_btn)
        self._queue_layout.addLayout(self._header_layout)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("queueScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(180)

        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(6, 6, 6, 6)
        self.tasks_layout.setSpacing(10)
        self.tasks_layout.addStretch()

        self.scroll.setWidget(self.tasks_container)
        self._queue_layout.addWidget(self.scroll)

        self.empty_label = QLabel("暂无下载任务")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setObjectName("muted")
        self.tasks_layout.insertWidget(0, self.empty_label)

        self._root_layout.addWidget(self._queue_group)

    def add_task(self, task: DownloadTask):
        if task.id in self._task_widgets:
            return

        self.empty_label.setVisible(False)

        widget = ProgressWidget(task)
        if self._metrics is not None:
            widget.apply_ui_metrics(self._metrics)
        widget.pause_clicked.connect(self.pause_task.emit)
        widget.resume_clicked.connect(self.resume_task.emit)
        widget.cancel_clicked.connect(self.cancel_task.emit)
        widget.retry_clicked.connect(self.retry_task.emit)
        widget.open_file_clicked.connect(self.open_file.emit)
        widget.open_folder_clicked.connect(self.open_folder.emit)

        self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, widget)
        self._task_widgets[task.id] = widget
        self._schedule_count_refresh()

    def update_task(self, task_id: str, task: DownloadTask):
        if task_id not in self._task_widgets:
            return

        widget = self._task_widgets[task_id]
        status_changed = task.status != widget.displayed_status
        if status_changed or not task.is_active:
            self._pending_updates.pop(task_id, None)
            widget.update_task(task)
            self._schedule_count_refresh()
            return

        self._pending_updates[task_id] = task
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def update_tasks(self, tasks: Dict[str, DownloadTask]):
        if not tasks:
            return

        self.begin_bulk_update()
        try:
            for task_id, task in tasks.items():
                widget = self._task_widgets.get(task_id)
                if widget is None:
                    continue
                self._pending_updates.pop(task_id, None)
                widget.apply_task(task)
        finally:
            self.end_bulk_update()

    def remove_task(self, task_id: str):
        if task_id not in self._task_widgets:
            return

        self._pending_updates.pop(task_id, None)
        widget = self._task_widgets.pop(task_id)
        self.tasks_layout.removeWidget(widget)
        widget.deleteLater()

        self._schedule_count_refresh()
        if not self._task_widgets:
            self.empty_label.setVisible(True)

    def clear_all(self):
        to_remove = []
        for task_id, widget in self._task_widgets.items():
            if widget.task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                to_remove.append(task_id)

        for task_id in to_remove:
            self.remove_task(task_id)

    def begin_bulk_update(self):
        self._bulk_update_depth += 1
        if self._bulk_update_depth == 1:
            self.setUpdatesEnabled(False)

    def end_bulk_update(self):
        if self._bulk_update_depth == 0:
            return

        self._bulk_update_depth -= 1
        if self._bulk_update_depth == 0:
            self._flush_pending_updates()
            self.setUpdatesEnabled(True)
            self._update_count()
            self.update()

    def _update_count(self):
        total = len(self._task_widgets)
        active = sum(1 for widget in self._task_widgets.values() if widget.task.is_active)

        if active > 0:
            self.count_label.setText(f"({active}/{total} 下载中)")
        else:
            self.count_label.setText(f"({total})")

    def _schedule_count_refresh(self):
        if self._bulk_update_depth > 0:
            return
        self._update_count()

    def _flush_pending_updates(self):
        if not self._pending_updates:
            return

        updates = self._pending_updates
        self._pending_updates = {}
        for task_id, task in updates.items():
            widget = self._task_widgets.get(task_id)
            if widget is not None:
                widget.apply_task(task)

    def get_task_count(self) -> int:
        return len(self._task_widgets)

    def get_active_count(self) -> int:
        return sum(1 for widget in self._task_widgets.values() if widget.task.is_active)

    def apply_ui_metrics(self, metrics):
        self._metrics = metrics
        self._queue_layout.setContentsMargins(
            metrics.choose(10, 12, 14),
            metrics.choose(8, 10, 12),
            metrics.choose(10, 12, 14),
            metrics.choose(10, 12, 14),
        )
        self._queue_layout.setSpacing(metrics.choose(6, 8, 10))
        self._header_layout.setSpacing(metrics.choose(6, 8, 10))
        self.clear_btn.setFixedHeight(metrics.choose(30, 32, 34))
        self.scroll.setMinimumHeight(metrics.choose(150, 180, 220))
        self.tasks_layout.setContentsMargins(
            metrics.choose(4, 6, 8),
            metrics.choose(4, 6, 8),
            metrics.choose(4, 6, 8),
            metrics.choose(4, 6, 8),
        )
        self.tasks_layout.setSpacing(metrics.choose(8, 10, 12))

        for widget in self._task_widgets.values():
            widget.apply_ui_metrics(metrics)
