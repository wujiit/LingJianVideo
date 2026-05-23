"""
yt-dlp wrapper for video downloading
"""
import copy
import hashlib
import json
import os
import multiprocessing
import queue
import sys
import re
import shlex
import time
from collections import OrderedDict
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path

# Lazy import yt_dlp to improve startup speed
yt_dlp = None

from .video_info import VideoInfo, FormatInfo


CANCELLED_ERROR = "operation_cancelled"
DOWNLOAD_CANCELLED_ERROR = "download_cancelled"
INFO_CACHE_TTL_SECONDS = 300
INFO_CACHE_MAX_ITEMS = 16
INFO_DISK_CACHE_TTL_SECONDS = 6 * 3600
INFO_DISK_CACHE_MAX_ITEMS = 128


def _extract_video_info_worker(url: str, ydl_opts: Dict[str, Any], result_queue) -> None:
    """Run yt-dlp metadata extraction in a separate process."""
    global yt_dlp

    try:
        if yt_dlp is None:
            import yt_dlp as yt_dlp_module
            yt_dlp = yt_dlp_module

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        result_queue.put({"info": info})
    except Exception as exc:
        try:
            result_queue.put({"error": str(exc)})
        except Exception:
            pass


class YtdlpWrapper:
    """Wrapper class for yt-dlp operations"""
    
    def __init__(self, ffmpeg_path: str = None):
        """
        Initialize the wrapper
        
        Args:
            ffmpeg_path: Path to FFmpeg executable (optional)
        """
        self.ffmpeg_path = ffmpeg_path
        self._cancelled = False
        self._mp_context = multiprocessing.get_context("spawn")
        self._info_process = None
        self._info_queue = None
        self._info_cache = OrderedDict()
        app_data = os.environ.get("APPDATA", str(Path.home()))
        self._info_cache_dir = Path(app_data) / "VideoDownloadAssistant" / "info_cache"
        self._info_disk_cache_ttl_seconds = INFO_DISK_CACHE_TTL_SECONDS
        self._info_disk_cache_limit = INFO_DISK_CACHE_MAX_ITEMS

    @staticmethod
    def _ensure_ytdlp_loaded():
        global yt_dlp
        if yt_dlp is None:
            try:
                import yt_dlp as yt_dlp_module
                yt_dlp = yt_dlp_module
            except ImportError:
                raise ImportError("yt-dlp is not installed. Please install it with: pip install yt-dlp")
        return yt_dlp
    
    def get_version(self) -> str:
        """Get yt-dlp version"""
        try:
            return self._ensure_ytdlp_loaded().version.__version__
        except:
            return "unknown"
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is supported by yt-dlp
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid and supported
        """
        if not url or not url.strip():
            return False
        
        # Basic URL pattern check
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(url) is not None
    
    def extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text (supports multiple URLs)
        
        Args:
            text: Text containing URLs
            
        Returns:
            List of extracted URLs
        """
        url_pattern = re.compile(
            r'https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)', re.IGNORECASE)
        
        urls = url_pattern.findall(text)
        # Clean up URLs (remove trailing punctuation)
        cleaned = []
        for url in urls:
            url = url.rstrip('.,;:!?')
            if self.validate_url(url):
                cleaned.append(url)
        return cleaned
    
    def get_video_info(self, url: str, playlist: bool = True, options: Dict[str, Any] = None) -> Optional[VideoInfo]:
        """
        Get video information without downloading
        
        Args:
            url: Video URL
            playlist: Whether to extract playlist info
            options: Optional parsing options (proxy, user_agent, cookies_from_browser)
            
        Returns:
            VideoInfo object or None if failed
        """
        self._cancelled = False
        self._cleanup_info_process()
        options = options or {}
        cache_key = self._build_info_cache_key(url, playlist, options)
        cached_info = self._get_cached_video_info(cache_key)
        if cached_info is not None:
            return cached_info
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'no_color': True,
            'cachedir': False,  # Disable cache to avoid stale info
        }
        
        # User Agent (Critical for Douyin/Kuaishou)
        user_agent = options.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        ydl_opts['user_agent'] = user_agent
        
        # Proxy
        if options.get('proxy'):
            ydl_opts['proxy'] = options['proxy']
            
        # Cookies from browser
        if options.get('cookies_from_browser'):
            ydl_opts['cookiesfrombrowser'] = (options['cookies_from_browser'],)
        
        # Cookies from file
        if options.get('cookies_file'):
            ydl_opts['cookiefile'] = options['cookies_file']
            
        # Referer
        if options.get('referer'):
            ydl_opts['referer'] = options['referer']
        
        # HTTP Headers
        if options.get('http_headers'):
            ydl_opts['http_headers'] = options['http_headers']
        
        if not playlist:
            ydl_opts['noplaylist'] = True
        
        if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path
        
        if options.get('socket_timeout'):
            ydl_opts['socket_timeout'] = options['socket_timeout']
        
        if options.get('sleep_interval'):
            ydl_opts['sleep_interval'] = options['sleep_interval']
        
        if options.get('max_sleep_interval'):
            ydl_opts['max_sleep_interval'] = options['max_sleep_interval']
        
        if options.get('retry_sleep'):
            ydl_opts['retry_sleep'] = options['retry_sleep']
        
        try:
            info = self._extract_video_info_with_cancel(url, ydl_opts)
            if info is None:
                return None
            parsed_info = self._parse_info(info)
            self._cache_video_info(cache_key, parsed_info)
            return copy.deepcopy(parsed_info)
        except Exception as e:
            if str(e) == CANCELLED_ERROR:
                raise
            raise Exception(f"获取视频信息失败: {str(e)}")

    def _build_info_cache_key(self, url: str, playlist: bool, options: Dict[str, Any]) -> str:
        cache_options = {
            'playlist': playlist,
            'proxy': options.get('proxy', ''),
            'cookies_from_browser': options.get('cookies_from_browser', ''),
            'cookies_file': options.get('cookies_file', ''),
            'referer': options.get('referer', ''),
            'user_agent': options.get('user_agent', ''),
            'socket_timeout': options.get('socket_timeout', 0),
            'sleep_interval': options.get('sleep_interval', 0),
            'max_sleep_interval': options.get('max_sleep_interval', 0),
            'retry_sleep': options.get('retry_sleep', ''),
            'http_headers': options.get('http_headers') or {},
        }
        try:
            options_key = json.dumps(cache_options, sort_keys=True, ensure_ascii=False)
        except TypeError:
            options_key = repr(cache_options)
        return f"{url}::{options_key}"

    def _get_cached_video_info(self, cache_key: str) -> Optional[VideoInfo]:
        cached_entry = self._info_cache.get(cache_key)
        if cached_entry:
            cached_at, info = cached_entry
            if (time.monotonic() - cached_at) > INFO_CACHE_TTL_SECONDS:
                self._info_cache.pop(cache_key, None)
            else:
                self._info_cache.move_to_end(cache_key)
                return copy.deepcopy(info)

        disk_cached = self._load_video_info_from_disk(cache_key)
        if disk_cached is None:
            return None

        self._info_cache[cache_key] = (time.monotonic(), copy.deepcopy(disk_cached))
        self._info_cache.move_to_end(cache_key)
        while len(self._info_cache) > INFO_CACHE_MAX_ITEMS:
            self._info_cache.popitem(last=False)
        return copy.deepcopy(disk_cached)

    def _cache_video_info(self, cache_key: str, info: VideoInfo) -> None:
        self._info_cache[cache_key] = (time.monotonic(), copy.deepcopy(info))
        self._info_cache.move_to_end(cache_key)
        while len(self._info_cache) > INFO_CACHE_MAX_ITEMS:
            self._info_cache.popitem(last=False)
        self._save_video_info_to_disk(cache_key, info)

    def _disk_cache_path(self, cache_key: str) -> Path:
        digest = hashlib.sha1(cache_key.encode("utf-8")).hexdigest()
        return self._info_cache_dir / f"{digest}.json"

    def _load_video_info_from_disk(self, cache_key: str) -> Optional[VideoInfo]:
        cache_path = self._disk_cache_path(cache_key)
        if not cache_path.exists():
            return None

        try:
            if (time.time() - cache_path.stat().st_mtime) > self._info_disk_cache_ttl_seconds:
                cache_path.unlink()
                return None

            with open(cache_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)

            if not isinstance(payload, dict):
                cache_path.unlink()
                return None

            info = self._video_info_from_dict(payload)
            os.utime(cache_path, None)
            return info
        except Exception:
            try:
                cache_path.unlink()
            except Exception:
                pass
            return None

    def _save_video_info_to_disk(self, cache_key: str, info: VideoInfo) -> None:
        cache_path = self._disk_cache_path(cache_key)
        temp_path = cache_path.with_suffix(".tmp")

        try:
            self._info_cache_dir.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as fh:
                json.dump(self._video_info_to_dict(info), fh, ensure_ascii=False)
            os.replace(temp_path, cache_path)
            self._prune_disk_cache()
        except Exception:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass

    def _prune_disk_cache(self) -> None:
        try:
            files = [path for path in self._info_cache_dir.iterdir() if path.is_file()]
        except Exception:
            return

        now = time.time()
        valid_files = []
        for path in files:
            try:
                mtime = path.stat().st_mtime
            except Exception:
                continue

            if (now - mtime) > self._info_disk_cache_ttl_seconds:
                try:
                    path.unlink()
                except Exception:
                    pass
                continue

            valid_files.append((mtime, path))

        valid_files.sort(key=lambda item: item[0], reverse=True)
        for _, path in valid_files[self._info_disk_cache_limit:]:
            try:
                path.unlink()
            except Exception:
                pass

    def _format_info_to_dict(self, fmt: FormatInfo) -> Dict[str, Any]:
        return {
            "format_id": fmt.format_id,
            "ext": fmt.ext,
            "resolution": fmt.resolution,
            "width": fmt.width,
            "height": fmt.height,
            "fps": fmt.fps,
            "vcodec": fmt.vcodec,
            "acodec": fmt.acodec,
            "filesize": fmt.filesize,
            "filesize_approx": fmt.filesize_approx,
            "tbr": fmt.tbr,
            "abr": fmt.abr,
            "vbr": fmt.vbr,
            "format_note": fmt.format_note,
        }

    def _format_info_from_dict(self, data: Dict[str, Any]) -> FormatInfo:
        return FormatInfo(
            format_id=str(data.get("format_id", "")),
            ext=data.get("ext", ""),
            resolution=data.get("resolution", ""),
            width=int(data.get("width", 0) or 0),
            height=int(data.get("height", 0) or 0),
            fps=float(data.get("fps", 0) or 0),
            vcodec=data.get("vcodec", "none") or "none",
            acodec=data.get("acodec", "none") or "none",
            filesize=int(data.get("filesize", 0) or 0),
            filesize_approx=int(data.get("filesize_approx", 0) or 0),
            tbr=float(data.get("tbr", 0) or 0),
            abr=float(data.get("abr", 0) or 0),
            vbr=float(data.get("vbr", 0) or 0),
            format_note=data.get("format_note", ""),
        )

    def _video_info_to_dict(self, info: VideoInfo) -> Dict[str, Any]:
        return {
            "url": info.url,
            "title": info.title,
            "author": info.author,
            "channel": info.channel,
            "channel_url": info.channel_url,
            "duration": info.duration,
            "thumbnail": info.thumbnail,
            "description": info.description,
            "upload_date": info.upload_date,
            "view_count": info.view_count,
            "like_count": info.like_count,
            "formats": [self._format_info_to_dict(fmt) for fmt in info.formats],
            "is_playlist": info.is_playlist,
            "playlist_count": info.playlist_count,
            "playlist_title": info.playlist_title,
            "playlist_entries": [self._video_info_to_dict(entry) for entry in info.playlist_entries],
            "extractor": info.extractor,
            "video_id": info.video_id,
        }

    def _video_info_from_dict(self, data: Dict[str, Any]) -> VideoInfo:
        info = VideoInfo(
            url=data.get("url", ""),
            title=data.get("title", ""),
            author=data.get("author", ""),
            channel=data.get("channel", ""),
            channel_url=data.get("channel_url", ""),
            duration=int(data.get("duration", 0) or 0),
            thumbnail=data.get("thumbnail", ""),
            description=data.get("description", ""),
            upload_date=data.get("upload_date", ""),
            view_count=int(data.get("view_count", 0) or 0),
            like_count=int(data.get("like_count", 0) or 0),
            is_playlist=bool(data.get("is_playlist", False)),
            playlist_count=int(data.get("playlist_count", 0) or 0),
            playlist_title=data.get("playlist_title", ""),
            extractor=data.get("extractor", ""),
            video_id=data.get("video_id", ""),
        )
        info.formats = [
            self._format_info_from_dict(fmt)
            for fmt in (data.get("formats") or [])
            if fmt
        ]
        info.playlist_entries = [
            self._video_info_from_dict(entry)
            for entry in (data.get("playlist_entries") or [])
            if entry
        ]
        return info
    
    def _extract_video_info_with_cancel(self, url: str, ydl_opts: Dict[str, Any]) -> Optional[dict]:
        result = None
        result_queue = self._mp_context.Queue()
        process = self._mp_context.Process(
            target=_extract_video_info_worker,
            args=(url, dict(ydl_opts), result_queue),
            daemon=True,
        )
        self._info_queue = result_queue
        self._info_process = process
        process.start()

        try:
            while result is None:
                if self._cancelled:
                    self._terminate_info_process()
                    raise RuntimeError(CANCELLED_ERROR)
                try:
                    result = result_queue.get(timeout=0.1)
                except queue.Empty:
                    if process.is_alive():
                        continue
                    break

            if result is None:
                try:
                    result = result_queue.get_nowait()
                except queue.Empty:
                    result = None

            process.join(timeout=0.2)

            if self._cancelled:
                raise RuntimeError(CANCELLED_ERROR)

            if result is None:
                if process.exitcode not in (0, None):
                    raise RuntimeError(f"parse process exited with code {process.exitcode}")
                return None

            if result.get("error"):
                raise RuntimeError(result["error"])

            return result.get("info")
        finally:
            self._cleanup_info_process()

    def _terminate_info_process(self):
        process = self._info_process
        if not process:
            return
        try:
            if process.is_alive():
                process.terminate()
                process.join(timeout=0.5)
            if process.is_alive() and hasattr(process, "kill"):
                process.kill()
                process.join(timeout=0.5)
        except Exception:
            pass

    def _cleanup_info_process(self):
        process = self._info_process
        result_queue = self._info_queue
        self._info_process = None
        self._info_queue = None

        if process is not None:
            try:
                if process.is_alive():
                    process.join(timeout=0.1)
            except Exception:
                pass
            try:
                process.close()
            except Exception:
                pass

        if result_queue is not None:
            try:
                result_queue.close()
            except Exception:
                pass
            try:
                result_queue.cancel_join_thread()
            except Exception:
                pass

    def _parse_info(self, info: dict) -> VideoInfo:
        """Parse yt-dlp info dict to VideoInfo object"""
        # Check if it's a playlist
        is_playlist = info.get('_type') == 'playlist' or 'entries' in info
        
        video_info = VideoInfo(
            url=info.get('webpage_url') or info.get('url', ''),
            title=info.get('title', '未知标题'),
            author=info.get('uploader') or info.get('creator') or info.get('channel', ''),
            channel=info.get('channel') or info.get('uploader', ''),
            channel_url=info.get('channel_url') or info.get('uploader_url', ''),
            duration=int(info.get('duration', 0) or 0),
            thumbnail=info.get('thumbnail', ''),
            description=info.get('description', ''),
            upload_date=info.get('upload_date', ''),
            view_count=int(info.get('view_count', 0) or 0),
            like_count=int(info.get('like_count', 0) or 0),
            extractor=info.get('extractor', ''),
            video_id=info.get('id', ''),
            is_playlist=is_playlist,
        )
        
        # Parse formats
        formats = info.get('formats', [])
        if formats:
            video_info.formats = [self._parse_format(f) for f in formats if f]
        
        # Handle playlist
        if is_playlist:
            entries = info.get('entries', [])
            video_info.playlist_count = len(entries) if entries else info.get('playlist_count', 0)
            video_info.playlist_title = info.get('title', '')
            # Parse first few entries for preview
            if entries:
                for entry in entries[:10]:  # Only parse first 10
                    if entry:
                        try:
                            video_info.playlist_entries.append(self._parse_info(entry))
                        except:
                            pass
        
        return video_info
    
    def _parse_format(self, fmt: dict) -> FormatInfo:
        """Parse format dict to FormatInfo object"""
        return FormatInfo(
            format_id=str(fmt.get('format_id', '')),
            ext=fmt.get('ext', ''),
            resolution=fmt.get('resolution', ''),
            width=int(fmt.get('width', 0) or 0),
            height=int(fmt.get('height', 0) or 0),
            fps=float(fmt.get('fps', 0) or 0),
            vcodec=fmt.get('vcodec', 'none') or 'none',
            acodec=fmt.get('acodec', 'none') or 'none',
            filesize=int(fmt.get('filesize', 0) or 0),
            filesize_approx=int(fmt.get('filesize_approx', 0) or 0),
            tbr=float(fmt.get('tbr', 0) or 0),
            abr=float(fmt.get('abr', 0) or 0),
            vbr=float(fmt.get('vbr', 0) or 0),
            format_note=fmt.get('format_note', ''),
        )
    
    def download(self, url: str, options: Dict[str, Any],
                 progress_callback: Optional[Callable[[dict], None]] = None,
                 status_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Download video
        
        Args:
            url: Video URL
            options: Download options dictionary
            progress_callback: Callback for progress updates
            status_callback: Callback for status updates
            
        Returns:
            Path to downloaded file
        """
        self._ensure_ytdlp_loaded()
        self._cancelled = False
        downloaded_file = ""
        
        def progress_hook(d):
            if self._cancelled:
                raise RuntimeError(DOWNLOAD_CANCELLED_ERROR)
            
            if d['status'] == 'downloading':
                if progress_callback:
                    progress_callback({
                        'status': 'downloading',
                        'downloaded_bytes': d.get('downloaded_bytes', 0),
                        'total_bytes': d.get('total_bytes') or d.get('total_bytes_estimate', 0),
                        'speed': d.get('speed', 0),
                        'eta': d.get('eta', 0),
                        'filename': d.get('filename', ''),
                    })
            elif d['status'] == 'finished':
                nonlocal downloaded_file
                downloaded_file = d.get('filename', '')
                if status_callback:
                    status_callback('后处理中...')
            elif d['status'] == 'error':
                if status_callback:
                    status_callback('下载出错')
        
        ydl_opts = {
            'format': options.get('format') or options.get('format_id', 'bestvideo+bestaudio/best'),
            'outtmpl': options.get('outtmpl') or options.get('output_template', '%(title)s.%(ext)s'),
            'merge_output_format': options.get('merge_output_format') or options.get('merge_format', 'mp4'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'retries': options.get('retries', 3),
            'fragment_retries': options.get('fragment_retries', options.get('retries', 3)),
        }
        
        if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path
        
        if options.get('socket_timeout'):
            ydl_opts['socket_timeout'] = options['socket_timeout']
        
        if options.get('sleep_interval'):
            ydl_opts['sleep_interval'] = options['sleep_interval']
        
        if options.get('max_sleep_interval'):
            ydl_opts['max_sleep_interval'] = options['max_sleep_interval']
        
        if options.get('retry_sleep'):
            ydl_opts['retry_sleep'] = options['retry_sleep']
        
        if options.get('concurrent_fragments'):
            ydl_opts['concurrent_fragments'] = options['concurrent_fragments']
        
        if options.get('external_downloader'):
            ydl_opts['external_downloader'] = options['external_downloader']
        
        if options.get('external_downloader_args'):
            args = options['external_downloader_args']
            if isinstance(args, str):
                try:
                    args = shlex.split(args)
                except Exception:
                    args = [args]
            ydl_opts['external_downloader_args'] = args
        
        if options.get('postprocessors'):
            ydl_opts['postprocessors'] = options.get('postprocessors')
        else:
            postprocessors = []
            if options.get('extract_audio'):
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': options.get('audio_format', 'mp3'),
                    'preferredquality': options.get('audio_quality', '192'),
                })
            if options.get('embed_thumbnail'):
                postprocessors.append({'key': 'EmbedThumbnail'})
            if options.get('embed_subtitles'):
                postprocessors.append({'key': 'FFmpegEmbedSubtitle'})
            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors
        
        # Subtitles
        if options.get('writesubtitles'):
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitleslangs'] = options.get('subtitleslangs', ['en', 'zh'])
        elif options.get('write_subtitles'):
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitleslangs'] = options.get('subtitle_langs', 'en,zh').split(',')
        
        # Proxy
        if options.get('proxy'):
            ydl_opts['proxy'] = options['proxy']
        
        # Cookies
        if options.get('cookiefile'):
            ydl_opts['cookiefile'] = options['cookiefile']
        elif options.get('cookies_file'):
            ydl_opts['cookiefile'] = options['cookies_file']

        if options.get('cookiesfrombrowser'):
            ydl_opts['cookiesfrombrowser'] = options['cookiesfrombrowser']
        elif options.get('cookies_from_browser'):
            ydl_opts['cookiesfrombrowser'] = (options['cookies_from_browser'],)

        if options.get('user_agent'):
            ydl_opts['user_agent'] = options['user_agent']

        if options.get('referer'):
            ydl_opts['referer'] = options['referer']
        
        # Rate limit
        if options.get('ratelimit'):
            ydl_opts['ratelimit'] = options['ratelimit']
        elif options.get('rate_limit'):
            ydl_opts['ratelimit'] = options['rate_limit']
        
        # Output path handling
        output_path = options.get('output_path', '')
        if output_path:
            output_template = options.get('output_template', '%(title)s.%(ext)s')
            ydl_opts['outtmpl'] = os.path.join(output_path, output_template)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                final_file = downloaded_file
                postprocessors = ydl_opts.get('postprocessors', [])
                if final_file and postprocessors:
                    for pp in postprocessors:
                        key = pp.get('key')
                        if key == 'FFmpegExtractAudio':
                            ext = pp.get('preferredcodec')
                            if ext:
                                final_file = self._replace_extension(final_file, ext)
                            break
                        if key == 'FFmpegVideoConvertor':
                            ext = pp.get('preferedformat')
                            if ext:
                                final_file = self._replace_extension(final_file, ext)
                            break
            return final_file
        except Exception as e:
            if str(e) == DOWNLOAD_CANCELLED_ERROR:
                raise
            raise Exception(f"下载失败: {str(e)}")

    @staticmethod
    def _replace_extension(path: str, new_ext: str) -> str:
        root, _ = os.path.splitext(path)
        if not new_ext:
            return path
        ext = new_ext if new_ext.startswith('.') else f".{new_ext}"
        return f"{root}{ext}"
    
    def cancel(self):
        """Cancel current download"""
        self._cancelled = True
        self._terminate_info_process()

    def shutdown(self):
        """Release any background process or queue owned by the wrapper."""
        self._cancelled = True
        self._terminate_info_process()
        self._cleanup_info_process()
    
    def get_best_format_string(self, prefer_codec: str = 'h264', 
                                max_height: int = None,
                                audio_only: bool = False) -> str:
        """
        Generate format selection string for yt-dlp
        
        Args:
            prefer_codec: Preferred video codec (h264, h265, vp9, av1)
            max_height: Maximum video height (e.g., 1080 for 1080p)
            audio_only: Whether to download audio only
            
        Returns:
            Format selection string
        """
        if audio_only:
            return "bestaudio/best"
        
        # Build format string
        video_filter = "bestvideo"
        audio_filter = "bestaudio"
        
        # Height filter
        if max_height:
            video_filter = f"bestvideo[height<={max_height}]"
        
        # Codec preference
        codec_map = {
            'h264': ['avc', 'h264'],
            'h265': ['hevc', 'h265'],
            'vp9': ['vp9', 'vp09'],
            'av1': ['av01', 'av1'],
        }
        
        if prefer_codec in codec_map:
            codecs = codec_map[prefer_codec]
            # Try preferred codec first, then fallback
            codec_filters = []
            for codec in codecs:
                if max_height:
                    codec_filters.append(f"bestvideo[height<={max_height}][vcodec^={codec}]")
                else:
                    codec_filters.append(f"bestvideo[vcodec^={codec}]")
            
            video_filter = "/".join(codec_filters) + f"/{video_filter}"
        
        return f"{video_filter}+{audio_filter}/best"
    
    @staticmethod
    def is_available() -> bool:
        """Check if yt-dlp is available"""
        try:
            YtdlpWrapper._ensure_ytdlp_loaded()
            return True
        except ImportError:
            return False
    
    @staticmethod
    def get_supported_sites() -> List[str]:
        """Get list of supported sites"""
        try:
            module = YtdlpWrapper._ensure_ytdlp_loaded()
            extractors = module.extractor.gen_extractors()
            return [e.IE_NAME for e in extractors if hasattr(e, 'IE_NAME')]
        except:
            return []
