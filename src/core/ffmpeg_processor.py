"""
FFmpeg processor for media processing operations
"""
import os
import subprocess
import json
import sys
import re
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class MediaInfo:
    """Media file information"""
    duration: float = 0
    width: int = 0
    height: int = 0
    video_codec: str = ""
    audio_codec: str = ""
    video_bitrate: int = 0
    audio_bitrate: int = 0
    file_size: int = 0
    format_name: str = ""


@dataclass(frozen=True)
class RuntimeProfile:
    """Runtime tuning profile derived from CPU topology."""

    logical_cores: int
    decode_threads: int
    encode_threads: int
    filter_threads: int
    audio_threads: int
    preset_floor: Optional[str] = None


# Transcode presets
TRANSCODE_PRESETS = {
    'ultrafast': {
        'name': '极速',
        'description': '最快速度，较低质量',
        'preset': 'ultrafast',
        'crf': 28,
    },
    'fast': {
        'name': '快速',
        'description': '较快速度，适中质量',
        'preset': 'veryfast',
        'crf': 23,
    },
    'balanced': {
        'name': '平衡',
        'description': '速度与质量平衡',
        'preset': 'medium',
        'crf': 20,
    },
    'quality': {
        'name': '高质量',
        'description': '较慢速度，高质量',
        'preset': 'slow',
        'crf': 18,
    },
    'best': {
        'name': '最佳质量',
        'description': '最慢速度，最高质量',
        'preset': 'veryslow',
        'crf': 16,
    },
    'compatible': {
        'name': '兼容模式',
        'description': 'H.264 + AAC，最大兼容性',
        'vcodec': 'libx264',
        'acodec': 'aac',
        'preset': 'medium',
        'crf': 20,
    },
}


class FFmpegProcessor:
    """FFmpeg processor for media operations"""
    
    def __init__(self, ffmpeg_path: str = None, ffprobe_path: str = None):
        """
        Initialize FFmpeg processor
        
        Args:
            ffmpeg_path: Path to ffmpeg executable
            ffprobe_path: Path to ffprobe executable
        """
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
        self.ffprobe_path = ffprobe_path or self._find_ffprobe()
        
        # 如果提供了 ffmpeg 路径但没提供 ffprobe 路径，尝试在同级目录查找
        if self.ffmpeg_path and not ffprobe_path:
             ffmpeg_dir = os.path.dirname(self.ffmpeg_path)
             possible_probe = os.path.join(ffmpeg_dir, 'ffprobe.exe')
             if os.path.exists(possible_probe):
                 self.ffprobe_path = possible_probe

        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False
        self._video_encoder: Optional[str] = None
        self._runtime_profile = self._build_runtime_profile()

    @property
    def video_encoder(self) -> str:
        """Lazily detect the best encoder to keep startup light."""
        if self._video_encoder is None:
            self._video_encoder = self._detect_best_encoder()
        return self._video_encoder

    @property
    def runtime_profile(self) -> RuntimeProfile:
        """Expose the runtime tuning profile for UI/logging."""
        return self._runtime_profile

    def _build_runtime_profile(self) -> RuntimeProfile:
        cores = max(1, os.cpu_count() or 1)

        if cores <= 1:
            return RuntimeProfile(
                logical_cores=cores,
                decode_threads=1,
                encode_threads=1,
                filter_threads=1,
                audio_threads=1,
                preset_floor="veryfast",
            )

        if cores == 2:
            return RuntimeProfile(
                logical_cores=cores,
                decode_threads=1,
                encode_threads=2,
                filter_threads=1,
                audio_threads=1,
                preset_floor="medium",
            )

        if cores <= 4:
            return RuntimeProfile(
                logical_cores=cores,
                decode_threads=2,
                encode_threads=min(cores, 4),
                filter_threads=2,
                audio_threads=1,
            )

        if cores <= 8:
            return RuntimeProfile(
                logical_cores=cores,
                decode_threads=2,
                encode_threads=min(cores, 6),
                filter_threads=2,
                audio_threads=2,
            )

        return RuntimeProfile(
            logical_cores=cores,
            decode_threads=2,
            encode_threads=8,
            filter_threads=4,
            audio_threads=2,
        )

    def _threads_for_workload(self, workload: str) -> int:
        profile = self._runtime_profile
        if workload == "audio":
            return profile.audio_threads
        if workload == "copy":
            return profile.decode_threads
        return profile.encode_threads

    def _build_ffmpeg_command(self, workload: str = "encode", use_filters: bool = False) -> List[str]:
        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-nostdin",
            "-nostats",
            "-loglevel",
            "warning",
        ]

        threads = self._threads_for_workload(workload)
        if threads > 0:
            cmd.extend(["-threads", str(threads)])

        if use_filters and self._runtime_profile.filter_threads > 0:
            cmd.extend(["-filter_threads", str(self._runtime_profile.filter_threads)])

        return cmd

    def _resolve_preset_for_cpu(self, preset: str) -> str:
        floor = self._runtime_profile.preset_floor
        if not preset or not floor:
            return preset

        order = [
            "veryslow",
            "slower",
            "slow",
            "medium",
            "fast",
            "veryfast",
            "superfast",
            "ultrafast",
        ]
        index_map = {name: idx for idx, name in enumerate(order)}

        preset_idx = index_map.get(preset)
        floor_idx = index_map.get(floor)
        if preset_idx is None or floor_idx is None:
            return preset

        if preset_idx < floor_idx:
            return floor
        return preset

    @staticmethod
    def _normalize_ext(path_or_ext: str) -> str:
        if not path_or_ext:
            return ""
        ext = os.path.splitext(path_or_ext)[1] if "." in os.path.basename(path_or_ext) else path_or_ext
        return ext.lower().lstrip(".")

    @staticmethod
    def _is_audio_only(media_info: Optional[MediaInfo]) -> bool:
        if media_info is None:
            return False
        return not media_info.video_codec and bool(media_info.audio_codec)

    def can_stream_copy(self, media_info: Optional[MediaInfo], target_ext: str) -> bool:
        if media_info is None:
            return False

        target_ext = self._normalize_ext(target_ext)
        vcodec = (media_info.video_codec or "").lower()
        acodec = (media_info.audio_codec or "").lower()
        audio_only = self._is_audio_only(media_info)

        if audio_only:
            audio_rules = {
                "m4a": {"aac", "alac", "mp4a"},
                "mp3": {"mp3"},
                "flac": {"flac"},
                "wav": {"pcm_s16le", "pcm_s24le", "pcm_f32le"},
            }
            allowed_audio = audio_rules.get(target_ext)
            return bool(allowed_audio and acodec in allowed_audio)

        if target_ext == "mkv":
            return bool(vcodec or acodec)

        rules = {
            "mp4": (
                {"h264", "hevc", "av1", "mpeg4"},
                {"aac", "ac3", "eac3", "mp3", "alac", "mp4a"},
            ),
            "mov": (
                {"h264", "hevc", "prores", "mpeg4"},
                {"aac", "alac", "pcm_s16le", "pcm_s24le", "ac3", "mp3"},
            ),
            "avi": (
                {"h264", "mpeg4", "mpeg2video", "msmpeg4v3"},
                {"mp3", "ac3", "pcm_s16le", "aac"},
            ),
            "webm": (
                {"vp8", "vp9", "av1"},
                {"opus", "vorbis"},
            ),
        }

        allowed = rules.get(target_ext)
        if not allowed:
            return False

        allowed_video, allowed_audio = allowed
        if vcodec and vcodec not in allowed_video:
            return False
        if acodec and acodec not in allowed_audio:
            return False
        return bool(vcodec or acodec)

    @staticmethod
    def _append_trim_args(cmd: List[str], options: Dict[str, Any],
                          log_callback: Optional[Callable[[str], None]] = None) -> None:
        clip_start = str(options.get("clip_start", "") or "").strip()
        clip_end = str(options.get("clip_end", "") or "").strip()

        if clip_start:
            cmd.extend(["-ss", clip_start])
        if clip_end:
            cmd.extend(["-to", clip_end])

        if log_callback and (clip_start or clip_end):
            if clip_start and clip_end:
                log_callback(f"剪辑区间: {clip_start} -> {clip_end}")
            elif clip_start:
                log_callback(f"剪辑起点: {clip_start}")
            else:
                log_callback(f"剪辑终点: {clip_end}")

    def _detect_best_encoder(self) -> str:
        """Detect best available video encoder"""
        if not self.ffmpeg_path or not os.path.exists(self.ffmpeg_path):
            return 'libx264'
            
        try:
            cmd = [self.ffmpeg_path, '-encoders']
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                creationflags=creation_flags,
                encoding='utf-8',
                errors='ignore'
            )
            output = result.stdout
            
            # Check for libx264
            if re.search(r'V[A-Z\.]*D\s+libx264', output):
                return 'libx264'
                
            # Check for h264_mf (Windows Media Foundation)
            if re.search(r'V[A-Z\.]*D\s+h264_mf', output):
                return 'h264_mf'
                
            # Check for libopenh264
            if re.search(r'V[A-Z\.]*D\s+libopenh264', output):
                return 'libopenh264'
                
        except Exception:
            pass
            
        return 'libx264'  # Default fallback
    
    def _find_ffmpeg(self) -> str:
        """Find ffmpeg executable"""
        from utils.system_utils import find_ffmpeg_executable
        return find_ffmpeg_executable()
    
    def _find_ffprobe(self) -> str:
        """Find ffprobe executable"""
        base_path = os.path.dirname(os.path.abspath(__file__))
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            
        possible_paths = [
            'ffprobe.exe',
            os.path.join(base_path, 'ffprobe.exe'),
            os.path.join(base_path, 'bin', 'ffprobe.exe'),
            os.path.join(base_path, '_internal', 'bin', 'ffprobe.exe'),
            os.path.join(base_path, 'ffmpeg', 'bin', 'ffprobe.exe'),
            os.path.join(base_path, '..', '..', 'resources', 'bin', 'ffmpeg', 'ffprobe.exe'),
            os.path.join(base_path, '..', '..', 'bin', 'ffmpeg', 'ffprobe.exe'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return 'ffprobe'
    

    
    def is_available(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except:
            return False
    
    def get_version(self) -> str:
        """Get FFmpeg version"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                first_line = result.stdout.split('\n')[0]
                # Extract version number
                match = re.search(r'ffmpeg version (\S+)', first_line)
                if match:
                    return match.group(1)
                return first_line
        except:
            pass
        return "unknown"
    
    def get_media_info(self, file_path: str, log_callback: Optional[Callable[[str], None]] = None) -> Optional[MediaInfo]:
        """
        Get media file information using ffprobe
        
        Args:
            file_path: Path to media file
            log_callback: Log callback
            
        Returns:
            MediaInfo object or None
        """
        if not os.path.exists(file_path):
            if log_callback:
                log_callback(f"文件不存在: {file_path}")
            return None
            
        if not os.path.exists(self.ffprobe_path) and self.ffprobe_path != 'ffprobe':
            if log_callback:
                log_callback(f"FFprobe路径无效: {self.ffprobe_path}")
            # Try to continue anyway if it's in PATH
        
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=creation_flags,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                if log_callback:
                    log_callback(f"FFprobe执行失败 (code={result.returncode}):\n{result.stderr}")
                return None
            
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                if log_callback:
                    log_callback(f"FFprobe输出JSON解析失败: {e}\n输出内容: {result.stdout[:200]}...")
                return None
                
            info = MediaInfo()
            
            # Parse format info
            fmt = data.get('format', {})
            try:
                info.duration = float(fmt.get('duration', 0))
            except (ValueError, TypeError):
                info.duration = 0
                
            try:
                info.file_size = int(fmt.get('size', 0))
            except (ValueError, TypeError):
                info.file_size = 0
                
            info.format_name = fmt.get('format_name', '')
            
            # Parse streams
            for stream in data.get('streams', []):
                codec_type = stream.get('codec_type', '')
                
                if codec_type == 'video':
                    info.width = int(stream.get('width', 0))
                    info.height = int(stream.get('height', 0))
                    info.video_codec = stream.get('codec_name', '')
                    try:
                        info.video_bitrate = int(stream.get('bit_rate', 0))
                    except: pass
                elif codec_type == 'audio':
                    info.audio_codec = stream.get('codec_name', '')
                    try:
                        info.audio_bitrate = int(stream.get('bit_rate', 0))
                    except: pass
            
            return info
        except Exception as e:
            if log_callback:
                log_callback(f"获取媒体信息异常: {e}")
            return None
    
    def merge_video_audio(self, video_path: str, audio_path: str, 
                          output_path: str, 
                          progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """
        Merge video and audio files
        
        Args:
            video_path: Path to video file
            audio_path: Path to audio file  
            output_path: Output file path
            progress_callback: Callback for progress (0-100)
            
        Returns:
            True if successful
        """
        self._cancelled = False
        
        # Get duration for progress calculation
        video_info = self.get_media_info(video_path)
        duration = video_info.duration if video_info else 0
        
        cmd = self._build_ffmpeg_command('copy')
        cmd.extend([
            '-i', video_path,
            '-i', audio_path,
            '-c', 'copy',  # Stream copy (no re-encoding)
            '-y',  # Overwrite output
            '-progress', 'pipe:1',  # Progress output
            output_path
        ])
        
        return self._run_ffmpeg(cmd, duration, progress_callback)
    
    def extract_audio(self, input_path: str, output_path: str,
                      audio_format: str = 'mp3',
                      audio_quality: str = '192',
                      clip_start: str = '',
                      clip_end: str = '',
                      progress_callback: Optional[Callable[[float], None]] = None,
                      log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Extract audio from video file
        
        Args:
            input_path: Input video file path
            output_path: Output audio file path
            audio_format: Output format (mp3, m4a, flac, wav)
            audio_quality: Audio quality/bitrate (e.g., '192' for 192kbps)
            progress_callback: Progress callback
            log_callback: Log callback
            
        Returns:
            True if successful
        """
        self._cancelled = False
        
        if log_callback:
            log_callback(f"正在获取媒体信息: {input_path}")
            
        media_info = self.get_media_info(input_path, log_callback)
        duration = media_info.duration if media_info else 0
        
        if log_callback:
            if media_info:
                log_callback(f"媒体时长: {duration}s")
            else:
                log_callback("无法获取媒体信息 (ffprobe失败)，将尝试直接转换")
        
        if log_callback:
            profile = self._runtime_profile
            log_callback(
                f"CPU cores={profile.logical_cores}, ffmpeg threads={self._threads_for_workload('audio')}"
            )

        # Build command based on format
        cmd = self._build_ffmpeg_command('audio')
        cmd.extend([
            '-i', input_path,
        ])
        self._append_trim_args(
            cmd,
            {"clip_start": clip_start, "clip_end": clip_end},
            log_callback,
        )
        cmd.extend([
            '-vn',  # No video
        ])
        
        if audio_format == 'mp3':
            cmd.extend(['-acodec', 'libmp3lame', '-ab', f'{audio_quality}k'])
        elif audio_format == 'm4a':
            cmd.extend(['-acodec', 'aac', '-ab', f'{audio_quality}k'])
        elif audio_format == 'flac':
            cmd.extend(['-acodec', 'flac'])
        elif audio_format == 'wav':
            cmd.extend(['-acodec', 'pcm_s16le'])
        else:
            cmd.extend(['-acodec', 'copy'])
        
        cmd.extend([
            '-y',
            '-progress', 'pipe:1',
            output_path
        ])
        
        return self._run_ffmpeg(cmd, duration, progress_callback, log_callback)
    
    def compress_video(self, input_path: str, output_path: str,
                       target_size_mb: Optional[float] = None,
                       crf: Optional[int] = None,
                       preset: str = 'medium',
                       audio_bitrate: int = 128,
                       width_scale: Optional[float] = None,
                       progress_callback: Optional[Callable[[float], None]] = None,
                       log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Compress video to target size or using CRF/Quality
        """
        self._cancelled = False
        encoder = self.video_encoder
        requested_preset = preset
        preset = self._resolve_preset_for_cpu(preset)
        
        if log_callback:
            log_callback(f"正在准备压缩: {input_path}")
            log_callback(f"使用视频编码器: {encoder}")
            
        media_info = self.get_media_info(input_path, log_callback)
        duration = media_info.duration if media_info else 0
        original_bitrate = media_info.video_bitrate + media_info.audio_bitrate if media_info else 0
        
        if duration == 0 and target_size_mb is not None:
             if log_callback:
                 log_callback("无法获取视频时长，无法按目标大小压缩，将使用默认质量压缩")
             target_size_mb = None
             crf = 23

        cmd = self._build_ffmpeg_command(
            'encode',
            use_filters=bool(width_scale and width_scale < 1.0),
        )
        cmd.extend([
            '-i', input_path,
        ])
        
        # Audio encoding settings
        cmd.extend(['-c:a', 'aac', '-b:a', f'{audio_bitrate}k'])
        
        # Resolution scaling
        if width_scale and width_scale < 1.0:
            # Scale width, keep aspect ratio, ensure even dimensions
            cmd.extend(['-vf', f'scale=iw*{width_scale}:-2'])
            if log_callback:
                 log_callback(f"启用分辨率缩放: {int(width_scale*100)}%")
        
        # Video encoding settings
        if encoder == 'libx264':
            cmd.extend(['-c:v', 'libx264', '-preset', preset])
            if target_size_mb is None:
                if crf is None: crf = 23
                cmd.extend(['-crf', str(crf)])
                if log_callback: log_callback(f"使用CRF模式: {crf}")
                
        elif encoder == 'h264_mf':
            cmd.extend(['-c:v', 'h264_mf'])
            if target_size_mb is None:
                # Map CRF to Quality (0-100)
                # Lower quality value in h264_mf means worse quality? No, usually 0-100 where 100 is best.
                # Adjusted mapping for h264_mf:
                # CRF 18 (High) -> Quality 70
                # CRF 23 (Med)  -> Quality 55
                # CRF 28 (Low)  -> Quality 40
                if crf is None: crf = 23
                quality = 55
                if crf <= 18: quality = 70
                elif crf <= 23: quality = 55
                elif crf <= 28: quality = 40
                else: quality = 30
                
                cmd.extend(['-rate_control', 'quality', '-quality', str(quality)])
                if log_callback: log_callback(f"使用Quality模式: {quality} (对应CRF {crf})")
            else:
                # For target size with h264_mf, CBR might be safer for size control
                cmd.extend(['-rate_control', 'cbr'])
                
        elif encoder == 'libopenh264':
            cmd.extend(['-c:v', 'libopenh264'])
            if target_size_mb is None:
                if log_callback: log_callback("警告: libopenh264不支持CRF，使用默认比特率")
                pass

        if log_callback:
            profile = self._runtime_profile
            log_callback(
                f"CPU cores={profile.logical_cores}, ffmpeg threads={self._threads_for_workload('encode')}, filter_threads={profile.filter_threads}"
            )
            if requested_preset != preset:
                log_callback(f"Preset adjusted for low-core CPU: {requested_preset} -> {preset}")

        if target_size_mb is not None:
            # Calculate bitrate for target size
            target_total_bitrate = (target_size_mb * 8192) / duration  # kbps
            target_video_bitrate = target_total_bitrate - audio_bitrate
            
            # Safety check: Don't exceed original bitrate if we aren't scaling down significantly
            # But "compression" might imply just changing format. 
            # If target bitrate > original, warn user
            if original_bitrate > 0 and target_total_bitrate > (original_bitrate / 1000):
                 if log_callback:
                     log_callback(f"提示: 目标码率 ({int(target_total_bitrate)}k) 高于原始码率 ({int(original_bitrate/1000)}k)，文件可能会变大")
            
            if target_video_bitrate < 100:
                if log_callback:
                    log_callback(f"警告: 目标大小太小，计算出的视频码率为 {target_video_bitrate:.0f}k")
                target_video_bitrate = 100 
                
            if log_callback:
                log_callback(f"目标大小: {target_size_mb}MB, 时长: {duration:.1f}s")
                log_callback(f"计算码率: 总计 {target_total_bitrate:.0f}k, 视频 {target_video_bitrate:.0f}k")
            
            cmd.extend(['-b:v', f'{int(target_video_bitrate)}k'])
            # Add maxrate/bufsize for better rate control
            cmd.extend(['-maxrate', f'{int(target_video_bitrate * 1.2)}k'])
            cmd.extend(['-bufsize', f'{int(target_video_bitrate * 2)}k'])
            
        cmd.extend([
            '-y',
            '-progress', 'pipe:1',
            output_path
        ])
        
        return self._run_ffmpeg(cmd, duration, progress_callback, log_callback)

    def convert_format(self, input_path: str, output_path: str,
                       options: Dict[str, Any] = None,
                       progress_callback: Optional[Callable[[float], None]] = None,
                       log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Convert media to different format
        
        Args:
            input_path: Input file path
            output_path: Output file path
            options: Conversion options
            progress_callback: Progress callback
            log_callback: Log callback
            
        Returns:
            True if successful
        """
        self._cancelled = False
        options = options or {}
        
        if log_callback:
            log_callback(f"正在获取媒体信息: {input_path}")
            
        media_info = self.get_media_info(input_path, log_callback)
        duration = media_info.duration if media_info else 0
        
        if log_callback:
            if media_info:
                log_callback(f"媒体时长: {duration}s")
            else:
                log_callback("无法获取媒体信息 (ffprobe失败)，将尝试直接转换")
        
        target_ext = self._normalize_ext(options.get("target_ext") or output_path)

        # Video codec
        requested_vcodec = options.get('vcodec', 'copy')
        vcodec = requested_vcodec
        if requested_vcodec == 'libx264' and self.video_encoder != 'libx264':
            vcodec = self.video_encoder

        # Audio codec
        acodec = options.get('acodec', 'copy')

        if options.get("quick_copy") and self.can_stream_copy(media_info, target_ext):
            vcodec = 'copy'
            acodec = 'copy'
            if log_callback:
                log_callback(f"快速转换命中: 使用封装复制输出 .{target_ext}")
        elif options.get("quick_copy") and log_callback:
            log_callback("快速转换未命中，自动回退到转码模式")

        workload = 'copy' if vcodec == 'copy' and acodec == 'copy' else 'encode'
        cmd = self._build_ffmpeg_command(workload)
        cmd.extend([
            '-i', input_path,
        ])
        self._append_trim_args(cmd, options, log_callback)
        
        # Video codec
        cmd.extend(['-c:v', vcodec])
        cmd.extend(['-c:a', acodec])
        
        # Additional options
        if 'crf' in options and vcodec != 'copy':
            cmd.extend(['-crf', str(options['crf'])])
        
        if 'preset' in options and vcodec != 'copy':
            preset = self._resolve_preset_for_cpu(options['preset'])
            if vcodec in ('libx264', 'libopenh264'):
                cmd.extend(['-preset', preset])
            if log_callback and preset != options['preset']:
                log_callback(f"Preset adjusted for low-core CPU: {options['preset']} -> {preset}")
        
        if 'audio_bitrate' in options and acodec != 'copy':
            cmd.extend(['-b:a', f"{options['audio_bitrate']}k"])

        if log_callback:
            profile = self._runtime_profile
            log_callback(
                f"CPU cores={profile.logical_cores}, ffmpeg threads={self._threads_for_workload(workload)}, encoder={vcodec}"
            )
        
        cmd.extend([
            '-y',
            '-progress', 'pipe:1',
            output_path
        ])
        
        return self._run_ffmpeg(cmd, duration, progress_callback, log_callback)
    
    def transcode(self, input_path: str, output_path: str,
                  preset_name: str = 'balanced',
                  progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """
        Transcode file using a preset
        
        Args:
            input_path: Input file path
            output_path: Output file path
            preset_name: Preset name (ultrafast, fast, balanced, quality, best, compatible)
            progress_callback: Progress callback
            
        Returns:
            True if successful
        """
        preset = TRANSCODE_PRESETS.get(preset_name, TRANSCODE_PRESETS['balanced'])
        
        vcodec = preset.get('vcodec', 'libx264')
        
        # Adjust vcodec if libx264 is specified but not available
        if vcodec == 'libx264' and self.video_encoder != 'libx264':
             vcodec = self.video_encoder
        
        options = {
            'vcodec': vcodec,
            'acodec': preset.get('acodec', 'aac'),
            'preset': preset.get('preset', 'medium'),
            'crf': preset.get('crf', 20),
        }
        
        return self.convert_format(input_path, output_path, options, progress_callback)
    
    def _run_ffmpeg(self, cmd: List[str], duration: float,
                    progress_callback: Optional[Callable[[float], None]] = None,
                    log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Run FFmpeg command with progress tracking
        
        Args:
            cmd: FFmpeg command list
            duration: Media duration for progress calculation
            progress_callback: Progress callback (0-100)
            log_callback: Log callback
            
        Returns:
            True if successful
        """
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            # 确保命令中包含 ffmpeg 可执行文件的绝对路径
            if not os.path.exists(cmd[0]) and cmd[0] != 'ffmpeg':
                if log_callback:
                    log_callback(f"警告: FFmpeg路径可能无效: {cmd[0]}")
                
            if log_callback:
                log_callback(f"执行命令: {' '.join(cmd)}")
                
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout to avoid deadlock
                universal_newlines=True,
                creationflags=creation_flags,
                encoding='utf-8', 
                errors='replace',
                bufsize=1 # Line buffering
            )
            
            # Parse progress from stdout
            while True:
                if self._cancelled:
                    self._process.terminate()
                    if log_callback:
                        log_callback("用户取消操作")
                    return False
                
                # 使用 readline 读取一行
                line = self._process.stdout.readline()
                
                # 如果读取到空字符串且进程已结束，则退出循环
                if not line and self._process.poll() is not None:
                    break
                    
                if not line:
                    continue
                
                # Parse time progress
                if 'out_time_ms=' in line:
                    try:
                        val = line.split('=')[1].strip()
                        if val == 'N/A':
                            continue
                        time_ms = int(val)
                        current_time = time_ms / 1000000
                        if duration > 0 and progress_callback:
                            progress = min(100, (current_time / duration) * 100)
                            progress_callback(progress)
                    except:
                        pass
                elif log_callback and ('Error' in line or 'Warning' in line or 'failed' in line):
                     # Log errors/warnings directly
                     log_callback(line.strip())
            
            # Wait for process to finish
            self._process.wait()
            
            if self._process.returncode != 0:
                if log_callback:
                    log_callback(f"FFmpeg process exited with code {self._process.returncode}")
                return False
                
            return True
            
        except Exception as e:
            if log_callback:
                log_callback(f"FFmpeg执行异常: {str(e)}")
            print(f"FFmpeg execution exception: {e}")
            return False
        finally:
            self._process = None
    
    def cancel(self):
        """Cancel current operation"""
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except:
                pass

    def shutdown(self, timeout_ms: int = 1500):
        """Force-stop the active FFmpeg process and release pipe handles."""
        self._cancelled = True
        process = self._process
        if process is None:
            return

        try:
            process.terminate()
        except Exception:
            pass

        timeout_seconds = max(timeout_ms, 0) / 1000.0
        try:
            process.wait(timeout=timeout_seconds)
        except Exception:
            pass

        if process.poll() is None:
            try:
                process.kill()
            except Exception:
                pass
            try:
                process.wait(timeout=0.5)
            except Exception:
                pass

        for stream_name in ("stdout", "stderr", "stdin"):
            stream = getattr(process, stream_name, None)
            if stream is None:
                continue
            try:
                stream.close()
            except Exception:
                pass

        self._process = None
    
    @staticmethod
    def get_preset_info(preset_name: str) -> Optional[Dict[str, Any]]:
        """Get preset information"""
        return TRANSCODE_PRESETS.get(preset_name)
    
    @staticmethod
    def get_all_presets() -> Dict[str, Dict[str, Any]]:
        """Get all available presets"""
        return TRANSCODE_PRESETS.copy()
