"""
Download manager for handling download tasks
"""
import os
import time
from collections import deque
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker, QTimer

from core.ytdlp_wrapper import YtdlpWrapper
from core.ffmpeg_processor import FFmpegProcessor
from core.download_task import DownloadTask, TaskStatus, DownloadOptions
from core.video_info import VideoInfo
from controllers.smart_strategy import SmartStrategy


class DownloadWorker(QThread):
    """Worker thread for downloading"""
    progress = Signal(str, dict)  # task_id, progress_data
    status_changed = Signal(str, TaskStatus, str)  # task_id, status, message
    finished = Signal(str, bool, str)  # task_id, success, message
    
    def __init__(self, task: DownloadTask, ffmpeg_path: str = None):
        super().__init__()
        self.task = task
        self.wrapper = YtdlpWrapper(ffmpeg_path)
        self._cancelled = False
        self._paused = False
    
    def run(self):
        """Run the download"""
        try:
            self.status_changed.emit(self.task.id, TaskStatus.DOWNLOADING, "开始下载...")
            
            def on_progress(data):
                if self._cancelled:
                    raise Exception("下载已取消")
                while self._paused and not self._cancelled:
                    self.msleep(100)
                self.progress.emit(self.task.id, data)
            
            def on_status(msg):
                self.status_changed.emit(self.task.id, TaskStatus.PROCESSING, msg)
            
            options = self.task.options.to_ytdlp_opts()
            options['output_path'] = self.task.options.output_path
            options['output_template'] = self.task.options.output_template
            
            output_file = self.wrapper.download(
                self.task.url,
                options,
                progress_callback=on_progress,
                status_callback=on_status
            )
            
            self.task.output_file = output_file
            self.finished.emit(self.task.id, True, "下载完成")
            
        except Exception as e:
            error_msg = str(e)
            if "已取消" in error_msg:
                self.finished.emit(self.task.id, False, "已取消")
            else:
                self.finished.emit(self.task.id, False, error_msg)
    
    def pause(self):
        """Pause download"""
        self._paused = True
    
    def resume(self):
        """Resume download"""
        self._paused = False
    
    def cancel(self):
        """Cancel download"""
        self._cancelled = True
        self._paused = False
        self.wrapper.cancel()


class DownloadManager(QObject):
    """Manager for download tasks"""
    
    # Signals
    task_added = Signal(DownloadTask)
    task_removed = Signal(str)
    task_updated = Signal(str, DownloadTask)
    tasks_updated = Signal(object)
    progress_updated = Signal(str, float, float, int)  # task_id, percent, speed, eta
    status_changed = Signal(str, TaskStatus)
    task_completed = Signal(str, bool, str)  # task_id, success, message
    queue_updated = Signal()
    
    def __init__(self, ffmpeg_path: str = None):
        super().__init__()
        self._tasks: Dict[str, DownloadTask] = {}
        self._workers: Dict[str, DownloadWorker] = {}
        self._ffmpeg = FFmpegProcessor(ffmpeg_path)
        self._ffmpeg_path = self._ffmpeg.ffmpeg_path
        self._strategy = SmartStrategy()
        self._configured_max_concurrent = 3
        self._max_concurrent = 3
        self._mutex = QMutex()
        self._progress_emit_interval = 0.125
        self._last_progress_emit: Dict[str, float] = {}
        self._speed_samples = deque(maxlen=8)
        self._auto_adjust_interval = 6.0
        self._last_auto_adjust = 0.0
        self._pending_task_ids = deque()
        self._queued_task_ids: Set[str] = set()
        self._busy_task_ids: Set[str] = set()
        self._pending_task_updates: Dict[str, DownloadTask] = {}
        self._task_update_timer = QTimer(self)
        self._task_update_timer.setSingleShot(True)
        self._task_update_timer.setInterval(100)
        self._task_update_timer.timeout.connect(self._flush_task_updates)
        self._shutting_down = False

    def set_ffmpeg_path(self, ffmpeg_path: str):
        normalized = ffmpeg_path if ffmpeg_path and os.path.exists(ffmpeg_path) else self._ffmpeg._find_ffmpeg()
        self._ffmpeg_path = normalized
        self._ffmpeg.ffmpeg_path = normalized
        self._ffmpeg._video_encoder = None
        
        ffprobe_path = self._ffmpeg._find_ffprobe()
        if normalized and normalized.lower().endswith('ffmpeg.exe'):
            candidate = normalized.replace('ffmpeg.exe', 'ffprobe.exe')
            if os.path.exists(candidate):
                ffprobe_path = candidate
        self._ffmpeg.ffprobe_path = ffprobe_path
    
    @property
    def tasks(self) -> List[DownloadTask]:
        """Get all tasks"""
        return list(self._tasks.values())
    
    @property
    def active_count(self) -> int:
        """Get number of active downloads"""
        return sum(1 for t in self._tasks.values() if t.is_active)
    
    @property
    def pending_count(self) -> int:
        """Get number of pending downloads"""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)
    
    def set_max_concurrent(self, limit: int):
        """Set maximum concurrent downloads"""
        normalized = max(1, min(10, limit))
        self._configured_max_concurrent = normalized
        self._max_concurrent = normalized
        self._speed_samples.clear()
        self._last_auto_adjust = 0.0
        self._process_queue()
    
    def add_task(self, url: str, options: DownloadOptions = None,
                 video_info: VideoInfo = None) -> DownloadTask:
        """
        Add a new download task
        
        Args:
            url: Video URL
            options: Download options
            video_info: Pre-fetched video info (optional)
            
        Returns:
            Created DownloadTask
        """
        with QMutexLocker(self._mutex):
            task = DownloadTask(
                url=url,
                options=options or DownloadOptions(),
            )
            
            if video_info:
                task.title = video_info.title
                task.author = video_info.author
                task.duration = video_info.duration
                task.thumbnail = video_info.thumbnail
            
            self._tasks[task.id] = task
            self._enqueue_task(task.id)
        
        self.task_added.emit(task)
        self.queue_updated.emit()
        self._process_queue()
        return task
    
    def add_tasks_from_playlist(self, video_info: VideoInfo, 
                                 options: DownloadOptions = None) -> List[DownloadTask]:
        """
        Add tasks from a playlist
        
        Args:
            video_info: Playlist VideoInfo
            options: Download options
            
        Returns:
            List of created tasks
        """
        tasks = []
        with QMutexLocker(self._mutex):
            for entry in video_info.playlist_entries:
                task = DownloadTask(
                    url=entry.url,
                    options=options or DownloadOptions(),
                )
                task.title = entry.title
                task.author = entry.author
                task.duration = entry.duration
                task.thumbnail = entry.thumbnail
                self._tasks[task.id] = task
                self._enqueue_task(task.id)
                tasks.append(task)

        for task in tasks:
            self.task_added.emit(task)
        if tasks:
            self.queue_updated.emit()
            self._process_queue()
        return tasks
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a task"""
        with QMutexLocker(self._mutex):
            if task_id in self._tasks:
                task = self._tasks[task_id]
                
                # Cancel if running
                worker = self._workers.pop(task_id, None)
                if worker:
                    worker.cancel()
                    self._schedule_worker_cleanup(worker)
                self._busy_task_ids.discard(task_id)
                self._queued_task_ids.discard(task_id)
                self._last_progress_emit.pop(task_id, None)
                
                del self._tasks[task_id]
                self.task_removed.emit(task_id)
                self.queue_updated.emit()
                return True
        return False
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a task"""
        with QMutexLocker(self._mutex):
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.can_pause:
                    if task_id in self._workers:
                        self._workers[task_id].pause()
                    task.status = TaskStatus.PAUSED
                    self.status_changed.emit(task_id, TaskStatus.PAUSED)
                    self._queue_task_update(task_id, task, immediate=True)
                    return True
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task"""
        with QMutexLocker(self._mutex):
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.can_resume:
                    if task_id in self._workers:
                        self._workers[task_id].resume()
                        task.status = TaskStatus.DOWNLOADING
                    else:
                        task.status = TaskStatus.PENDING
                        self._enqueue_task(task_id, front=True)
                    self.status_changed.emit(task_id, task.status)
                    self._queue_task_update(task_id, task, immediate=True)
        
        self._process_queue()
        return True
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        with QMutexLocker(self._mutex):
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.can_cancel:
                    if task_id in self._workers:
                        self._workers[task_id].cancel()
                    task.status = TaskStatus.CANCELLED
                    self._queued_task_ids.discard(task_id)
                    self.status_changed.emit(task_id, TaskStatus.CANCELLED)
                    self._queue_task_update(task_id, task, immediate=True)
                    return True
        return False
    
    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        with QMutexLocker(self._mutex):
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                    task.status = TaskStatus.PENDING
                    task.retry_count += 1
                    task.error_message = ""
                    self._enqueue_task(task_id, front=True)
                    self.status_changed.emit(task_id, TaskStatus.PENDING)
                    self._queue_task_update(task_id, task, immediate=True)
        
        self._process_queue()
        return True
    
    def clear_completed(self):
        """Remove all completed tasks"""
        with QMutexLocker(self._mutex):
            to_remove = [
                task_id for task_id, task in self._tasks.items()
                if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
            ]
            for task_id in to_remove:
                self._queued_task_ids.discard(task_id)
                self._busy_task_ids.discard(task_id)
                self._last_progress_emit.pop(task_id, None)
                del self._tasks[task_id]
                self.task_removed.emit(task_id)
            self.queue_updated.emit()
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """Get a task by ID"""
        return self._tasks.get(task_id)
    
    def _process_queue(self):
        """Process pending tasks in queue"""
        if self._shutting_down:
            return
        with QMutexLocker(self._mutex):
            active = len(self._busy_task_ids)

            while active < self._max_concurrent and self._pending_task_ids:
                task_id = self._pending_task_ids.popleft()
                self._queued_task_ids.discard(task_id)
                task = self._tasks.get(task_id)
                if not task or task.status != TaskStatus.PENDING or task_id in self._busy_task_ids:
                    continue
                self._start_task(task)
                active += 1
    
    def _start_task(self, task: DownloadTask):
        """Start downloading a task"""
        task.status = TaskStatus.DOWNLOADING
        task.started_at = datetime.now()
        worker = DownloadWorker(task, self._ffmpeg_path)
        worker.progress.connect(self._on_progress)
        worker.status_changed.connect(self._on_status)
        worker.finished.connect(self._on_finished)
        
        self._workers[task.id] = worker
        self._busy_task_ids.add(task.id)
        worker.start()
        
        self.status_changed.emit(task.id, TaskStatus.DOWNLOADING)
        self._queue_task_update(task.id, task, immediate=True)

    def _enqueue_task(self, task_id: str, front: bool = False):
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING or task_id in self._queued_task_ids:
            return
        if front:
            self._pending_task_ids.appendleft(task_id)
        else:
            self._pending_task_ids.append(task_id)
        self._queued_task_ids.add(task_id)

    def _schedule_worker_cleanup(self, worker: Optional[DownloadWorker]):
        if worker is None:
            return
        if worker.isRunning():
            QTimer.singleShot(25, lambda worker=worker: self._schedule_worker_cleanup(worker))
            return
        worker.deleteLater()

    def _queue_task_update(self, task_id: str, task: DownloadTask, immediate: bool = False):
        if self._shutting_down:
            return

        self._pending_task_updates[task_id] = task
        if immediate:
            self._flush_task_updates()
            return

        if not self._task_update_timer.isActive():
            self._task_update_timer.start()

    def _flush_task_updates(self):
        if not self._pending_task_updates:
            return

        updates = dict(self._pending_task_updates)
        self._pending_task_updates.clear()
        self.tasks_updated.emit(updates)

    def _disconnect_worker_signals(self, worker: Optional[DownloadWorker]):
        if worker is None:
            return

        for signal_name in ("progress", "status_changed", "finished"):
            signal = getattr(worker, signal_name, None)
            if signal is None:
                continue
            try:
                signal.disconnect()
            except (TypeError, RuntimeError):
                pass

    def _shutdown_worker_resources(self, worker: Optional[DownloadWorker]):
        if worker is None:
            return

        wrapper = getattr(worker, "wrapper", None)
        if wrapper is not None and hasattr(wrapper, "shutdown"):
            try:
                wrapper.shutdown()
            except Exception:
                pass

    def _shutdown_worker(self, worker: Optional[DownloadWorker], timeout_ms: int = 1500):
        if worker is None:
            return

        self._disconnect_worker_signals(worker)

        try:
            worker.cancel()
        except Exception:
            pass

        self._shutdown_worker_resources(worker)

        if worker.isRunning():
            worker.wait(timeout_ms)

        if worker.isRunning():
            try:
                worker.terminate()
            except Exception:
                pass
            worker.wait(500)

        self._shutdown_worker_resources(worker)

        worker.deleteLater()

    def _apply_ffmpeg_fallback(self, task: DownloadTask) -> bool:
        if self._ffmpeg.is_available():
            return False
        if task.options.extract_audio:
            task.options.extract_audio = False
            task.options.format_id = 'bestaudio/best'
        else:
            current = task.options.format_id or ''
            if '+' in current or 'bestvideo' in current:
                task.options.format_id = 'best[ext=mp4]/best'
            else:
                task.options.format_id = 'best[ext=mp4]/best'
            task.options.merge_format = 'mp4'
        task.options.embed_thumbnail = False
        task.options.embed_subtitles = False
        return True
    
    def _on_progress(self, task_id: str, data: dict):
        """Handle progress update"""
        if self._shutting_down:
            return
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.update_progress(data)
            now = time.monotonic()
            self._maybe_adjust_concurrent(now)
            last_emit = self._last_progress_emit.get(task_id)
            should_emit = (
                last_emit is None or
                (now - last_emit) >= self._progress_emit_interval or
                task.progress.percent >= 100
            )
            if should_emit:
                self._last_progress_emit[task_id] = now
                self.progress_updated.emit(
                    task_id,
                    task.progress.percent,
                    task.progress.speed,
                    task.progress.eta
                )
                self._queue_task_update(task_id, task, immediate=False)

    def _maybe_adjust_concurrent(self, now: float):
        active_speeds = [
            task.progress.speed
            for task in self._tasks.values()
            if task.status == TaskStatus.DOWNLOADING and task.progress.speed > 0
        ]

        if not active_speeds:
            return

        self._speed_samples.append(sum(active_speeds))

        if (now - self._last_auto_adjust) < self._auto_adjust_interval:
            return

        if self.pending_count == 0 and self._max_concurrent == self._configured_max_concurrent:
            return

        average_speed = sum(self._speed_samples) / len(self._speed_samples)
        average_speed_mb = average_speed / (1024 * 1024)
        suggested = self._strategy.adjust_concurrent(average_speed_mb, self._max_concurrent)
        suggested = max(1, min(self._configured_max_concurrent, suggested))
        self._last_auto_adjust = now

        if suggested == self._max_concurrent:
            return

        self._max_concurrent = suggested
        self.queue_updated.emit()
        self._process_queue()
    
    def _on_status(self, task_id: str, status: TaskStatus, message: str):
        """Handle status change"""
        if self._shutting_down:
            return
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = status
            self.status_changed.emit(task_id, status)
            self._queue_task_update(task_id, task, immediate=True)
    
    def _on_finished(self, task_id: str, success: bool, message: str):
        """Handle task completion"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.completed_at = datetime.now()
            self._busy_task_ids.discard(task_id)
            
            # Clean up worker
            worker = self._workers.pop(task_id, None)
            if worker is not None:
                self._schedule_worker_cleanup(worker)
            self._last_progress_emit.pop(task_id, None)

            if self._shutting_down:
                if task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    task.status = TaskStatus.COMPLETED if success else TaskStatus.CANCELLED
                return
            
            if success:
                task.status = TaskStatus.COMPLETED
            else:
                if "已取消" in message:
                    task.status = TaskStatus.CANCELLED
                else:
                    if task.retry_count < task.max_retries and self._apply_ffmpeg_fallback(task):
                        task.retry_count += 1
                        task.error_message = ""
                        task.status = TaskStatus.PENDING
                        self._enqueue_task(task_id, front=True)
                        self.status_changed.emit(task_id, task.status)
                        self._queue_task_update(task_id, task, immediate=True)
                        self.queue_updated.emit()
                        self._process_queue()
                        return
                    if self._apply_auto_fallback(task, message):
                        task.status = TaskStatus.PENDING
                        self._enqueue_task(task_id, front=True)
                        self.status_changed.emit(task_id, task.status)
                        self._queue_task_update(task_id, task, immediate=True)
                        self.queue_updated.emit()
                        self._process_queue()
                        return
                    task.status = TaskStatus.FAILED
                    task.error_message = message
            
            self.task_completed.emit(task_id, success, message)
            self.status_changed.emit(task_id, task.status)
            self._queue_task_update(task_id, task, immediate=True)
            self.queue_updated.emit()

            if not any(t.is_active for t in self._tasks.values()):
                self._speed_samples.clear()
                self._last_auto_adjust = 0.0
                self._max_concurrent = self._configured_max_concurrent
        
        # Process next in queue
        self._process_queue()

    def _apply_auto_fallback(self, task: DownloadTask, message: str) -> bool:
        if task.retry_count >= task.max_retries:
            return False
        original_options = task.options.to_ytdlp_opts()
        original_options['url'] = task.url
        fallback = self._strategy.auto_fallback(message, original_options)
        if not fallback:
            return False
        if 'format' in fallback:
            task.options.format_id = fallback['format']
        if 'merge_format' in fallback:
            task.options.merge_format = fallback['merge_format']
        if 'merge_output_format' in fallback:
            task.options.merge_format = fallback['merge_output_format']
        if 'rate_limit' in fallback:
            task.options.rate_limit = fallback['rate_limit']
        task.retry_count += 1
        task.error_message = ""
        return True
    
    def shutdown(self):
        """Shutdown manager and cancel all tasks"""
        with QMutexLocker(self._mutex):
            if self._shutting_down:
                return

            self._shutting_down = True
            if self._task_update_timer.isActive():
                self._task_update_timer.stop()
            self._pending_task_updates.clear()
            workers = list(self._workers.values())
            self._workers.clear()

            for task in self._tasks.values():
                if task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    task.status = TaskStatus.CANCELLED

            self._busy_task_ids.clear()
            self._queued_task_ids.clear()
            self._pending_task_ids.clear()
            self._last_progress_emit.clear()

        for worker in workers:
            self._shutdown_worker(worker)

        self._speed_samples.clear()
        self._last_auto_adjust = 0.0
        self._max_concurrent = self._configured_max_concurrent
