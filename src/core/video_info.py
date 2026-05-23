"""
Video and Format information data models
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class MediaType(Enum):
    """Media type enumeration"""
    VIDEO = "video"
    AUDIO = "audio"
    VIDEO_AUDIO = "video+audio"


@dataclass
class FormatInfo:
    """Information about a specific format option"""
    format_id: str
    ext: str
    resolution: str = ""
    width: int = 0
    height: int = 0
    fps: float = 0
    vcodec: str = "none"
    acodec: str = "none"
    filesize: int = 0
    filesize_approx: int = 0
    tbr: float = 0  # total bitrate in kbps
    abr: float = 0  # audio bitrate in kbps
    vbr: float = 0  # video bitrate in kbps
    format_note: str = ""
    
    @property
    def has_video(self) -> bool:
        return self.vcodec != "none" and self.vcodec is not None
    
    @property
    def has_audio(self) -> bool:
        return self.acodec != "none" and self.acodec is not None
    
    @property
    def media_type(self) -> MediaType:
        if self.has_video and self.has_audio:
            return MediaType.VIDEO_AUDIO
        elif self.has_video:
            return MediaType.VIDEO
        else:
            return MediaType.AUDIO
    
    @property
    def size_mb(self) -> float:
        """Get file size in MB"""
        size = self.filesize or self.filesize_approx
        return size / (1024 * 1024) if size else 0
    
    @property
    def quality_label(self) -> str:
        """Get human-readable quality label"""
        if self.height >= 2160:
            return "4K"
        elif self.height >= 1440:
            return "2K"
        elif self.height >= 1080:
            return "1080p"
        elif self.height >= 720:
            return "720p"
        elif self.height >= 480:
            return "480p"
        elif self.height >= 360:
            return "360p"
        elif self.height > 0:
            return f"{self.height}p"
        elif self.has_audio and not self.has_video:
            return "音频"
        else:
            return "未知"
    
    @property
    def codec_info(self) -> str:
        """Get codec information string"""
        parts = []
        if self.has_video:
            codec = self.vcodec.split('.')[0] if self.vcodec else ""
            if 'avc' in codec.lower() or 'h264' in codec.lower():
                parts.append("H.264")
            elif 'hevc' in codec.lower() or 'h265' in codec.lower():
                parts.append("H.265")
            elif 'vp9' in codec.lower():
                parts.append("VP9")
            elif 'av01' in codec.lower() or 'av1' in codec.lower():
                parts.append("AV1")
            else:
                parts.append(codec)
        if self.has_audio:
            codec = self.acodec.split('.')[0] if self.acodec else ""
            if 'mp4a' in codec.lower() or 'aac' in codec.lower():
                parts.append("AAC")
            elif 'opus' in codec.lower():
                parts.append("Opus")
            elif 'mp3' in codec.lower():
                parts.append("MP3")
            elif 'flac' in codec.lower():
                parts.append("FLAC")
            else:
                parts.append(codec)
        return " + ".join(parts) if parts else "未知"
    
    def __str__(self) -> str:
        size_str = f"{self.size_mb:.1f}MB" if self.size_mb > 0 else "未知大小"
        return f"{self.quality_label} ({self.ext}) - {self.codec_info} - {size_str}"


@dataclass
class VideoInfo:
    """Information about a video"""
    url: str
    title: str = ""
    author: str = ""
    channel: str = ""
    channel_url: str = ""
    duration: int = 0  # in seconds
    thumbnail: str = ""
    description: str = ""
    upload_date: str = ""
    view_count: int = 0
    like_count: int = 0
    formats: List[FormatInfo] = field(default_factory=list)
    is_playlist: bool = False
    playlist_count: int = 0
    playlist_title: str = ""
    playlist_entries: List['VideoInfo'] = field(default_factory=list)
    extractor: str = ""  # e.g., "youtube", "bilibili"
    video_id: str = ""
    
    @property
    def duration_str(self) -> str:
        """Get human-readable duration string"""
        if self.duration <= 0:
            return "未知"
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    @property
    def video_formats(self) -> List[FormatInfo]:
        """Get only video formats (with video stream)"""
        return [f for f in self.formats if f.has_video]
    
    @property
    def audio_formats(self) -> List[FormatInfo]:
        """Get only audio formats (audio only)"""
        return [f for f in self.formats if f.has_audio and not f.has_video]
    
    @property
    def combined_formats(self) -> List[FormatInfo]:
        """Get formats that have both video and audio"""
        return [f for f in self.formats if f.has_video and f.has_audio]
    
    @property
    def best_video_format(self) -> Optional[FormatInfo]:
        """Get the best quality video format"""
        video_formats = self.video_formats
        if not video_formats:
            return None
        # Sort by height (resolution), then by bitrate
        return max(video_formats, key=lambda f: (f.height, f.tbr or 0))
    
    @property
    def best_audio_format(self) -> Optional[FormatInfo]:
        """Get the best quality audio format"""
        audio_formats = self.audio_formats
        if not audio_formats:
            return None
        # Sort by audio bitrate
        return max(audio_formats, key=lambda f: f.abr or f.tbr or 0)
    
    @property
    def available_resolutions(self) -> List[str]:
        """Get list of available resolutions"""
        resolutions = set()
        for f in self.video_formats:
            if f.height > 0:
                resolutions.add(f.quality_label)
        # Sort by resolution (descending)
        order = ["4K", "2K", "1080p", "720p", "480p", "360p", "240p", "144p"]
        return [r for r in order if r in resolutions]
    
    def get_formats_by_resolution(self, resolution: str) -> List[FormatInfo]:
        """Get all formats matching a resolution"""
        return [f for f in self.video_formats if f.quality_label == resolution]
    
    def estimate_size(self, format_id: str = None) -> float:
        """Estimate download size in MB"""
        if format_id:
            for f in self.formats:
                if f.format_id == format_id:
                    return f.size_mb
        # Estimate based on best quality
        best_video = self.best_video_format
        best_audio = self.best_audio_format
        total = 0
        if best_video:
            total += best_video.size_mb
        if best_audio:
            total += best_audio.size_mb
        return total
    
    @property
    def site_name(self) -> str:
        """Get friendly site name"""
        site_names = {
            'youtube': 'YouTube',
            'bilibili': 'Bilibili',
            'twitter': 'Twitter/X',
            'tiktok': 'TikTok',
            'douyin': '抖音',
            'weibo': '微博',
            'instagram': 'Instagram',
            'facebook': 'Facebook',
            'vimeo': 'Vimeo',
            'twitch': 'Twitch',
        }
        extractor_lower = self.extractor.lower()
        for key, name in site_names.items():
            if key in extractor_lower:
                return name
        return self.extractor or "未知网站"
