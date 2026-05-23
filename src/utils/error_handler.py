"""
Error handler with user-friendly error messages
"""
from typing import Dict


# Error message translations
ERROR_MESSAGES: Dict[str, str] = {
    # Network errors
    'ERROR: Video unavailable': '视频不可用，可能已被删除或设为私密',
    'ERROR: Private video': '这是私密视频，需要登录才能访问',
    'ERROR: This video is available for registered users only': '此视频仅对注册用户开放',
    'ERROR: Sign in to confirm your age': '需要登录并验证年龄才能观看',
    'ERROR: Video is private': '视频已设为私密',
    'ERROR: This video has been removed': '视频已被删除',
    
    # Access errors
    'ERROR: Unable to extract': '无法解析视频信息，请检查链接是否正确',
    'ERROR: Unsupported URL': '不支持此链接，请检查链接格式',
    'ERROR: HTTP Error 403': '访问被拒绝，可能需要使用代理或登录',
    'ERROR: HTTP Error 404': '视频不存在或链接无效',
    'ERROR: HTTP Error 429': '请求过于频繁，请稍后再试',
    'ERROR: HTTP Error 503': '服务暂时不可用，请稍后再试',
    
    # Format errors
    'ERROR: No video formats found': '未找到可下载的视频格式',
    'ERROR: Requested format is not available': '所选格式不可用，请尝试其他格式',
    'ERROR: Requested format not available': '所选格式不可用，请尝试其他格式',
    
    # FFmpeg errors
    'ERROR: ffmpeg not found': 'FFmpeg 未安装或路径配置错误',
    'ERROR: ffprobe not found': 'FFprobe 未找到，请检查 FFmpeg 安装',
    'ERROR: Postprocessing': '后处理失败，请检查 FFmpeg 配置',
    
    # Download errors
    'ERROR: unable to download': '下载失败，请检查网络连接',
    'ERROR: Connection refused': '连接被拒绝，请检查网络或代理设置',
    'ERROR: Connection timed out': '连接超时，请检查网络连接',
    'ERROR: Network is unreachable': '网络不可达，请检查网络连接',
    
    # File errors
    'ERROR: File already exists': '文件已存在',
    'ERROR: Unable to write': '无法写入文件，请检查磁盘空间和权限',
    'PermissionError': '没有写入权限，请更换下载目录',
    'No space left': '磁盘空间不足',
    
    # Geographic restrictions
    'ERROR: This video is not available in your country': '此视频在您所在的地区不可用，请尝试使用代理',
    'ERROR: Content not available': '内容不可用，可能存在地区限制',
    
    # Age restrictions
    'ERROR: Content Warning': '内容包含年龄限制，需要登录验证',
    
    # Login required
    'ERROR: Login required': '需要登录才能访问此内容',
    'ERROR: Cookies required': '需要提供 Cookies 才能访问',
    
    # Rate limiting
    'too many requests': '请求过于频繁，请稍后再试',
    'rate limit': '触发速率限制，请稍后再试',
}


def translate_error(error_message: str) -> str:
    """
    Translate technical error message to user-friendly text
    
    Args:
        error_message: Original error message
        
    Returns:
        User-friendly error message in Chinese
    """
    if not error_message:
        return "发生未知错误"
    
    error_lower = error_message.lower()
    
    # Check for known error patterns
    for pattern, friendly in ERROR_MESSAGES.items():
        if pattern.lower() in error_lower:
            return friendly
    
    # Generic translations based on keywords
    if 'timeout' in error_lower:
        return '连接超时，请检查网络连接'
    if 'connection' in error_lower and 'refused' in error_lower:
        return '连接被拒绝，请检查网络或代理设置'
    if 'ssl' in error_lower or 'certificate' in error_lower:
        return 'SSL 证书错误，请检查网络环境'
    if 'proxy' in error_lower:
        return '代理连接失败，请检查代理设置'
    if 'dns' in error_lower:
        return 'DNS 解析失败，请检查网络连接'
    if 'permission' in error_lower:
        return '权限不足，请检查文件或目录权限'
    if 'disk' in error_lower or 'space' in error_lower:
        return '磁盘空间不足'
    if 'memory' in error_lower:
        return '内存不足'
    if 'cancelled' in error_lower or '已取消' in error_message:
        return '操作已取消'
    if 'interrupted' in error_lower:
        return '下载被中断'
    if 'merge' in error_lower:
        return '音视频合并失败，请检查 FFmpeg 配置'
    if 'extract' in error_lower:
        return '视频解析失败，可能是链接格式不正确'
    if 'ffmpeg' in error_lower:
        return 'FFmpeg 处理出错，请检查 FFmpeg 安装'
    
    # If no match, return a generic message with original error
    if len(error_message) > 200:
        error_message = error_message[:200] + "..."
    
    return f"下载出错：{error_message}"


class ErrorHandler:
    """Error handler utility class"""
    
    @staticmethod
    def translate(error: Exception) -> str:
        """Translate exception to user-friendly message"""
        return translate_error(str(error))
    
    @staticmethod
    def is_network_error(error_message: str) -> bool:
        """Check if error is network-related"""
        network_keywords = [
            'connection', 'timeout', 'network', 'dns', 'ssl',
            'http error', 'proxy', 'unreachable', 'refused',
        ]
        error_lower = error_message.lower()
        return any(kw in error_lower for kw in network_keywords)
    
    @staticmethod
    def is_permission_error(error_message: str) -> bool:
        """Check if error is permission-related"""
        permission_keywords = [
            'permission', 'access denied', 'forbidden', 'login',
            'private', 'authenticate', 'sign in',
        ]
        error_lower = error_message.lower()
        return any(kw in error_lower for kw in permission_keywords)
    
    @staticmethod
    def is_format_error(error_message: str) -> bool:
        """Check if error is format-related"""
        format_keywords = [
            'format', 'codec', 'merge', 'mux', 'ffmpeg',
        ]
        error_lower = error_message.lower()
        return any(kw in error_lower for kw in format_keywords)
    
    @staticmethod
    def suggest_solution(error_message: str) -> str:
        """Suggest a solution based on error type"""
        error_lower = error_message.lower()
        
        if 'proxy' in error_lower or '403' in error_message:
            return "建议：尝试设置代理或更换网络环境"
        if 'timeout' in error_lower or 'connection' in error_lower:
            return "建议：检查网络连接，或尝试降低并发数"
        if 'format' in error_lower:
            return "建议：尝试选择其他格式或降低画质"
        if 'ffmpeg' in error_lower:
            return "建议：检查 FFmpeg 是否正确安装"
        if 'permission' in error_lower:
            return "建议：更换下载目录或以管理员身份运行"
        if 'login' in error_lower or 'cookies' in error_lower:
            return "建议：在浏览器登录后导出 Cookies 使用"
        if '429' in error_message or 'rate' in error_lower:
            return "建议：等待几分钟后重试，或降低并发数"
        if 'country' in error_lower or 'region' in error_lower:
            return "建议：使用代理访问"
        
        return ""
