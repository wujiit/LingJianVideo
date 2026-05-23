"""
Download task model and status tracking
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class TaskStatus(Enum):
    """Download task status."""

    PENDING = "pending"
    PARSING = "parsing"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    """Download progress information."""

    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: float = 0
    eta: int = 0
    percent: float = 0
    filename: str = ""

    @property
    def speed_str(self) -> str:
        """Get human-readable speed string."""
        if self.speed <= 0:
            return "0 B/s"
        if self.speed < 1024:
            return f"{self.speed:.0f} B/s"
        if self.speed < 1024 * 1024:
            return f"{self.speed / 1024:.1f} KB/s"
        return f"{self.speed / (1024 * 1024):.2f} MB/s"

    @property
    def eta_str(self) -> str:
        """Get human-readable ETA string."""
        if self.eta <= 0:
            return "--:--"
        if self.eta < 60:
            return f"{self.eta}秒"
        if self.eta < 3600:
            minutes = self.eta // 60
            seconds = self.eta % 60
            return f"{minutes}分{seconds}秒"
        hours = self.eta // 3600
        minutes = (self.eta % 3600) // 60
        return f"{hours}小时{minutes}分"

    @property
    def downloaded_str(self) -> str:
        """Get human-readable downloaded size."""
        return self._format_bytes(self.downloaded_bytes)

    @property
    def total_str(self) -> str:
        """Get human-readable total size."""
        return self._format_bytes(self.total_bytes)

    @staticmethod
    def _format_bytes(size: int) -> str:
        if size <= 0:
            return "0 B"
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


@dataclass
class DownloadOptions:
    """Download options for a task."""

    format_id: str = "bestvideo+bestaudio/best"
    output_path: str = ""
    output_template: str = "%(title)s.%(ext)s"
    merge_format: str = "mp4"
    recode_video: str = ""
    extract_audio: bool = False
    audio_format: str = "mp3"
    audio_quality: str = "192"
    embed_thumbnail: bool = False
    embed_subtitles: bool = False
    write_subtitles: bool = False
    subtitle_langs: str = "en,zh"
    proxy: str = ""
    cookies_file: str = ""
    cookies_from_browser: str = ""
    user_agent: str = ""
    referer: str = ""
    rate_limit: str = ""
    retries: int = 3
    fragment_retries: int = 3
    request_timeout: int = 15
    sleep_interval: float = 0
    max_sleep_interval: float = 0
    retry_sleep: str = ""
    concurrent_fragments: int = 0
    external_downloader: str = ""
    external_downloader_args: str = ""
    post_process_preset: str = "none"
    delete_source_after_post_process: bool = False

    def to_ytdlp_opts(self) -> Dict[str, Any]:
        """Convert to yt-dlp options dictionary."""
        opts = {
            "format": self.format_id,
            "outtmpl": self.output_template,
            "merge_output_format": self.merge_format,
            "retries": self.retries,
        }

        postprocessors = []
        if self.extract_audio:
            postprocessors.append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.audio_format,
                    "preferredquality": self.audio_quality,
                }
            )
        if self.embed_thumbnail:
            postprocessors.append({"key": "EmbedThumbnail"})
        if self.embed_subtitles:
            postprocessors.append({"key": "FFmpegEmbedSubtitle"})
        if self.recode_video and not self.extract_audio:
            postprocessors.append(
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": self.recode_video,
                }
            )
        if postprocessors:
            opts["postprocessors"] = postprocessors

        if self.write_subtitles or self.embed_subtitles:
            opts["writesubtitles"] = True
            opts["subtitleslangs"] = self.subtitle_langs.split(",")

        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        if self.cookies_from_browser:
            opts["cookiesfrombrowser"] = (self.cookies_from_browser,)
        if self.user_agent:
            opts["user_agent"] = self.user_agent
        if self.referer:
            opts["referer"] = self.referer
        if self.rate_limit:
            opts["ratelimit"] = self.rate_limit
        if self.fragment_retries:
            opts["fragment_retries"] = self.fragment_retries
        if self.request_timeout:
            opts["socket_timeout"] = self.request_timeout
        if self.sleep_interval:
            opts["sleep_interval"] = self.sleep_interval
        if self.max_sleep_interval:
            opts["max_sleep_interval"] = self.max_sleep_interval
        if self.retry_sleep:
            opts["retry_sleep"] = self.retry_sleep
        if self.concurrent_fragments:
            opts["concurrent_fragments"] = self.concurrent_fragments
        if self.external_downloader:
            opts["external_downloader"] = self.external_downloader
        if self.external_downloader_args:
            opts["external_downloader_args"] = self.external_downloader_args

        return opts


@dataclass
class DownloadTask:
    """A download task."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    url: str = ""
    title: str = ""
    author: str = ""
    duration: int = 0
    thumbnail: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    options: DownloadOptions = field(default_factory=DownloadOptions)
    output_file: str = ""
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

    @property
    def status_text(self) -> str:
        """Get human-readable status text."""
        status_map = {
            TaskStatus.PENDING: "等待中",
            TaskStatus.PARSING: "解析中",
            TaskStatus.DOWNLOADING: "下载中",
            TaskStatus.PROCESSING: "处理中",
            TaskStatus.PAUSED: "已暂停",
            TaskStatus.COMPLETED: "已完成",
            TaskStatus.FAILED: "失败",
            TaskStatus.CANCELLED: "已取消",
        }
        return status_map.get(self.status, "未知")

    @property
    def can_pause(self) -> bool:
        """Check if task can be paused."""
        return self.status in (TaskStatus.DOWNLOADING, TaskStatus.PENDING)

    @property
    def can_resume(self) -> bool:
        """Check if task can be resumed."""
        return self.status in (TaskStatus.PAUSED, TaskStatus.FAILED)

    @property
    def can_cancel(self) -> bool:
        """Check if task can be cancelled."""
        return self.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)

    @property
    def is_active(self) -> bool:
        """Check if task is actively running."""
        return self.status in (
            TaskStatus.DOWNLOADING,
            TaskStatus.PARSING,
            TaskStatus.PROCESSING,
        )

    @property
    def duration_str(self) -> str:
        """Get human-readable duration string."""
        if self.duration <= 0:
            return "未知"
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def update_progress(self, data: dict):
        """Update progress from yt-dlp callback data."""
        self.progress.downloaded_bytes = data.get("downloaded_bytes", 0)
        self.progress.total_bytes = data.get("total_bytes") or data.get(
            "total_bytes_estimate", 0
        )
        self.progress.speed = data.get("speed", 0) or 0
        self.progress.eta = data.get("eta", 0) or 0
        self.progress.filename = data.get("filename", "")

        if self.progress.total_bytes > 0:
            self.progress.percent = (
                self.progress.downloaded_bytes / self.progress.total_bytes
            ) * 100
        else:
            self.progress.percent = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "duration": self.duration,
            "status": self.status.value,
            "output_file": self.output_file,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadTask":
        """Create from dictionary."""
        task = cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            title=data.get("title", ""),
            author=data.get("author", ""),
            duration=data.get("duration", 0),
            status=TaskStatus(data.get("status", "pending")),
            output_file=data.get("output_file", ""),
            error_message=data.get("error_message", ""),
        )
        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        return task
