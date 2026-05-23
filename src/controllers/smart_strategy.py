"""
Smart strategy system for intelligent downloading
"""
import re
import os
from typing import Optional, Dict, Any, List, Tuple
from core.video_info import VideoInfo, FormatInfo


class SmartStrategy:
    """Smart strategy for intelligent downloading decisions"""
    
    # Codec compatibility order (most compatible first)
    CODEC_COMPATIBILITY = {
        'video': ['h264', 'avc', 'h265', 'hevc', 'vp9', 'av1'],
        'audio': ['aac', 'mp4a', 'mp3', 'opus', 'flac'],
    }
    
    # Format compatibility
    FORMAT_COMPATIBILITY = ['mp4', 'mkv', 'webm', 'mov', 'avi']
    
    # Illegal filename characters
    ILLEGAL_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
    
    def __init__(self):
        self._history: List[Dict[str, Any]] = []
    
    def recommend_format(self, video_info: VideoInfo, 
                         prefer_quality: str = 'best',
                         prefer_codec: str = 'h264',
                         max_size_mb: float = None) -> Dict[str, Any]:
        """
        Recommend the best download format based on video info
        
        Args:
            video_info: Video information
            prefer_quality: Quality preference ('best', '1080p', '720p', etc.)
            prefer_codec: Preferred video codec
            max_size_mb: Maximum file size in MB
            
        Returns:
            Recommended format options
        """
        result = {
            'format_string': 'bestvideo+bestaudio/best',
            'merge_format': 'mp4',
            'video_format': None,
            'audio_format': None,
            'estimated_size_mb': 0,
            'needs_transcode': False,
            'quality_note': '',
        }
        
        video_formats = video_info.video_formats
        audio_formats = video_info.audio_formats
        
        if not video_formats:
            # Audio only or no formats available
            if audio_formats:
                best_audio = video_info.best_audio_format
                result['format_string'] = best_audio.format_id if best_audio else 'bestaudio'
                result['video_format'] = None
                result['audio_format'] = best_audio
                result['quality_note'] = '仅音频'
            return result
        
        # Filter by quality preference
        target_height = self._parse_quality(prefer_quality)
        if target_height:
            video_formats = [f for f in video_formats if f.height <= target_height]
        
        # Filter by size limit
        if max_size_mb:
            video_formats = [f for f in video_formats if f.size_mb <= max_size_mb * 0.9]
        
        if not video_formats:
            video_formats = video_info.video_formats  # Fallback to all
        
        # Find best video format
        best_video = self._select_best_video(video_formats, prefer_codec)
        best_audio = video_info.best_audio_format
        
        if best_video:
            result['video_format'] = best_video
            
            # Build format string
            if best_audio:
                result['format_string'] = f"{best_video.format_id}+{best_audio.format_id}"
                result['audio_format'] = best_audio
            else:
                result['format_string'] = best_video.format_id
            
            # Determine output format
            if best_video.ext in ['webm'] or (best_audio and best_audio.ext in ['webm', 'opus']):
                # Check if needs transcode for compatibility
                if prefer_codec == 'h264':
                    result['needs_transcode'] = True
                    result['merge_format'] = 'mp4'
                else:
                    result['merge_format'] = 'mkv'  # MKV supports most codecs
            else:
                result['merge_format'] = 'mp4'
            
            # Estimate size
            size = best_video.size_mb
            if best_audio:
                size += best_audio.size_mb
            result['estimated_size_mb'] = size
            
            # Quality note
            result['quality_note'] = f"{best_video.quality_label} {best_video.codec_info}"
        
        return result
    
    def _parse_quality(self, quality: str) -> Optional[int]:
        """Parse quality string to height"""
        quality_map = {
            'best': None,
            '4k': 2160,
            '2160p': 2160,
            '2k': 1440,
            '1440p': 1440,
            '1080p': 1080,
            '720p': 720,
            '480p': 480,
            '360p': 360,
        }
        return quality_map.get(quality.lower())
    
    def _select_best_video(self, formats: List[FormatInfo], 
                           prefer_codec: str = 'h264') -> Optional[FormatInfo]:
        """Select best video format with codec preference"""
        if not formats:
            return None
        
        # Sort by height descending
        formats = sorted(formats, key=lambda f: (-f.height, -f.tbr))
        
        # Try to find format with preferred codec at best quality
        best_height = formats[0].height
        candidates = [f for f in formats if f.height == best_height]
        
        # Score by codec preference
        def codec_score(fmt: FormatInfo) -> int:
            codec = fmt.vcodec.lower() if fmt.vcodec else ''
            if prefer_codec in codec or prefer_codec.replace('h', '') in codec:
                return 100
            for i, c in enumerate(self.CODEC_COMPATIBILITY['video']):
                if c in codec:
                    return 50 - i * 5
            return 0
        
        candidates.sort(key=lambda f: (-codec_score(f), -f.tbr))
        return candidates[0] if candidates else formats[0]
    
    def auto_fallback(self, error_message: str, 
                      original_options: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate fallback options when download fails
        
        Args:
            error_message: Error message from failed download
            original_options: Original download options
            
        Returns:
            New options to try, or None if no fallback available
        """
        error_lower = error_message.lower()
        new_options = original_options.copy()
        
        # Format not available
        if 'format' in error_lower and ('not available' in error_lower or 'unavailable' in error_lower):
            # Try simpler format string
            current = new_options.get('format', '')
            if '+' in current:
                # Try best combined
                new_options['format'] = 'best'
                return new_options
            elif 'bestvideo' in current:
                new_options['format'] = 'best[height<=720]'
                return new_options
        
        # Merge or ffmpeg error
        if any(key in error_lower for key in ['merge', 'muxing', 'ffmpeg', 'postprocess']):
            url = new_options.get('url', '')
            url_lower = url.lower() if isinstance(url, str) else ''
            if 'youtube' in url_lower or 'youtu.be' in url_lower or 'youtube-nocookie.com' in url_lower:
                new_options['format'] = 'best[ext=mp4]'
                new_options['merge_format'] = 'mp4'
                return new_options
            current = new_options.get('format', '')
            if '+' in current or 'bestvideo' in current:
                new_options['format'] = 'best[ext=mp4]/best'
                new_options['merge_format'] = 'mp4'
                return new_options
            new_options['merge_format'] = 'mkv'
            return new_options
        
        # Rate limit / HTTP error
        if '429' in error_lower or 'rate' in error_lower:
            new_options['rate_limit'] = '500K'  # Slow down
            return new_options
        
        # No fallback available
        return None
    
    def adjust_concurrent(self, download_speed_mbps: float, 
                          current_limit: int) -> int:
        """
        Adjust concurrent downloads based on network speed
        
        Args:
            download_speed_mbps: Current download speed in Mbps
            current_limit: Current concurrent limit
            
        Returns:
            Suggested new limit
        """
        if download_speed_mbps < 1:  # < 1 Mbps
            return max(1, current_limit - 1)
        elif download_speed_mbps < 5:  # 1-5 Mbps
            return min(2, current_limit)
        elif download_speed_mbps < 20:  # 5-20 Mbps
            return min(3, current_limit + 1)
        else:  # > 20 Mbps
            return min(5, current_limit + 1)
    
    def clean_filename(self, filename: str, max_length: int = 200) -> str:
        """
        Clean filename by removing illegal characters
        
        Args:
            filename: Original filename
            max_length: Maximum filename length
            
        Returns:
            Cleaned filename
        """
        # Remove illegal characters
        cleaned = re.sub(self.ILLEGAL_CHARS, '_', filename)
        
        # Remove leading/trailing dots and spaces
        cleaned = cleaned.strip('. ')
        
        # Replace multiple underscores/spaces
        cleaned = re.sub(r'[_\s]+', ' ', cleaned)
        
        # Truncate if too long
        if len(cleaned) > max_length:
            # Try to keep extension
            parts = cleaned.rsplit('.', 1)
            if len(parts) == 2 and len(parts[1]) <= 10:
                name, ext = parts
                cleaned = name[:max_length - len(ext) - 1] + '.' + ext
            else:
                cleaned = cleaned[:max_length]
        
        # Fallback if empty
        if not cleaned:
            cleaned = 'download'
        
        return cleaned
    
    def suggest_output_folder(self, video_info: VideoInfo, 
                               base_path: str) -> str:
        """
        Suggest output folder based on video info
        
        Args:
            video_info: Video information
            base_path: Base download path
            
        Returns:
            Suggested folder path
        """
        if video_info.is_playlist:
            # Create folder for playlist
            folder_name = self.clean_filename(
                video_info.playlist_title or video_info.title or 'playlist'
            )
            return os.path.join(base_path, folder_name)
        
        if video_info.channel:
            # Optionally organize by channel
            channel_name = self.clean_filename(video_info.channel)
            return os.path.join(base_path, channel_name)
        
        return base_path
    
    def build_output_template(self, naming_rule: str = '{title}') -> str:
        """
        Build yt-dlp output template from naming rule
        
        Args:
            naming_rule: Naming rule with placeholders
            
        Returns:
            yt-dlp output template
        """
        # Map user-friendly placeholders to yt-dlp template
        mappings = {
            '{title}': '%(title)s',
            '{author}': '%(uploader)s',
            '{channel}': '%(channel)s',
            '{date}': '%(upload_date)s',
            '{id}': '%(id)s',
            '{resolution}': '%(resolution)s',
            '{ext}': '%(ext)s',
        }
        
        template = naming_rule
        for placeholder, ytdlp_var in mappings.items():
            template = template.replace(placeholder, ytdlp_var)
        
        # Ensure extension is included
        if '%(ext)s' not in template:
            template += '.%(ext)s'
        
        return template
    
    def estimate_download_time(self, size_mb: float, 
                                speed_mbps: float) -> int:
        """
        Estimate download time in seconds
        
        Args:
            size_mb: File size in MB
            speed_mbps: Download speed in MB/s
            
        Returns:
            Estimated seconds
        """
        if speed_mbps <= 0:
            return 0
        return int(size_mb / speed_mbps)
    
    def should_extract_audio_only(self, title: str, 
                                   duration: int) -> bool:
        """
        Guess if user might want audio only based on content
        
        Args:
            title: Video title
            duration: Video duration in seconds
            
        Returns:
            True if likely audio content
        """
        audio_keywords = [
            'music', 'song', 'audio', 'podcast', 'album', 'track',
            '音乐', '歌曲', '专辑', '播客', '纯音乐', 'mv',
        ]
        
        title_lower = title.lower()
        for keyword in audio_keywords:
            if keyword in title_lower:
                return True
        
        # Long content might be podcast/audio
        if duration > 3600:  # > 1 hour
            return True
        
        return False
    
    def get_quality_options(self, video_info: VideoInfo) -> List[Dict[str, Any]]:
        """
        Get available quality options for UI display
        
        Args:
            video_info: Video information
            
        Returns:
            List of quality options
        """
        options = []
        
        # Best quality option
        best = self.recommend_format(video_info, 'best')
        options.append({
            'label': f"最佳画质 - {best['quality_note']}",
            'value': 'best',
            'format_string': best['format_string'],
            'size_mb': best['estimated_size_mb'],
        })
        
        # Resolution-specific options
        for resolution in video_info.available_resolutions:
            rec = self.recommend_format(video_info, resolution)
            if rec['video_format']:
                options.append({
                    'label': f"{resolution} - {rec['video_format'].codec_info}",
                    'value': resolution,
                    'format_string': rec['format_string'],
                    'size_mb': rec['estimated_size_mb'],
                })
        
        # Audio only option
        if video_info.audio_formats:
            best_audio = video_info.best_audio_format
            options.append({
                'label': f"仅音频 - {best_audio.codec_info if best_audio else 'Best'}",
                'value': 'audio',
                'format_string': 'bestaudio/best',
                'size_mb': best_audio.size_mb if best_audio else 0,
            })
        
        return options
