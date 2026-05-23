"""
Shared media presets for conversion, compression, and post-download actions.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from utils.file_utils import FileUtils


CONVERSION_PRESETS: Dict[str, Dict[str, Any]] = {
    "quick_mp4": {
        "label": "快速转 MP4",
        "description": "优先直接封装到 MP4，必要时再转码。",
        "mode": "video",
        "target_format": "mp4",
        "quick_copy": True,
        "vcodec": "libx264",
        "acodec": "aac",
        "preset": "veryfast",
        "crf": 23,
        "quality_label": "快速",
        "suffix": "quick",
    },
    "compatible_mp4": {
        "label": "兼容 MP4",
        "description": "兼容性优先，适合播放器、剪辑软件和分享。",
        "mode": "video",
        "target_format": "mp4",
        "quick_copy": False,
        "vcodec": "libx264",
        "acodec": "aac",
        "preset": "medium",
        "crf": 21,
        "quality_label": "平衡",
        "suffix": "compatible",
    },
    "small_mp4": {
        "label": "省空间 MP4",
        "description": "体积优先，适合发群、发盘和长期存放。",
        "mode": "video",
        "target_format": "mp4",
        "quick_copy": False,
        "vcodec": "libx264",
        "acodec": "aac",
        "preset": "veryfast",
        "crf": 28,
        "quality_label": "极速",
        "suffix": "small",
    },
    "archive_mkv": {
        "label": "保真 MKV",
        "description": "尽量保留原始编码，适合留档和后续再处理。",
        "mode": "video",
        "target_format": "mkv",
        "quick_copy": True,
        "vcodec": "copy",
        "acodec": "copy",
        "preset": "medium",
        "crf": 20,
        "quality_label": "最佳质量",
        "suffix": "archive",
    },
    "extract_mp3": {
        "label": "提取 MP3",
        "description": "导出 MP3 音频，适合通用播放器和车机。",
        "mode": "audio",
        "target_format": "mp3",
        "audio_quality": "192k",
        "suffix": "audio",
    },
    "extract_m4a": {
        "label": "提取 M4A",
        "description": "导出 M4A 音频，体积更省一些。",
        "mode": "audio",
        "target_format": "m4a",
        "audio_quality": "192k",
        "suffix": "audio",
    },
}


COMPRESSION_PRESETS: Dict[str, Dict[str, Any]] = {
    "balanced": {
        "label": "通用压缩",
        "description": "画质和体积比较均衡，适合大多数素材。",
        "mode": "quality",
        "crf": 23,
        "preset": "medium",
        "width_scale": 1.0,
        "quality_label": "推荐 (CRF 23)",
    },
    "share_720p": {
        "label": "分享优先",
        "description": "更适合微信、钉钉、网盘和网页上传。",
        "mode": "quality",
        "crf": 26,
        "preset": "veryfast",
        "width_scale": 0.75,
        "quality_label": "自定义",
    },
    "storage_first": {
        "label": "省空间",
        "description": "尽量减小文件体积，适合存档和低带宽传输。",
        "mode": "quality",
        "crf": 30,
        "preset": "veryfast",
        "width_scale": 0.5,
        "quality_label": "自定义",
    },
    "target_50mb": {
        "label": "50MB 目标文件",
        "description": "快速压到较小体积，适合临时分享。",
        "mode": "target_size",
        "target_size": 50.0,
        "preset": "veryfast",
        "width_scale": 0.75,
    },
}


DOWNLOAD_POST_PROCESS_PRESETS: Dict[str, Dict[str, Any]] = {
    "none": {
        "label": "不处理",
        "description": "下载完成后直接保留原文件。",
        "action": "none",
    },
    "quick_mp4": {
        "label": "下载后转 MP4（快速）",
        "description": "优先直接封装为 MP4，适合常规播放和分享。",
        "action": "convert",
        "conversion_preset": "quick_mp4",
    },
    "compatible_mp4": {
        "label": "下载后转 MP4（兼容）",
        "description": "统一为兼容 MP4，适合播放器和剪辑工具。",
        "action": "convert",
        "conversion_preset": "compatible_mp4",
    },
    "extract_mp3": {
        "label": "下载后提取 MP3",
        "description": "自动导出 MP3 音频文件。",
        "action": "convert",
        "conversion_preset": "extract_mp3",
    },
    "share_compress": {
        "label": "下载后压缩（分享版）",
        "description": "自动压小一版，适合即时发送和上传。",
        "action": "compress",
        "compression_preset": "share_720p",
        "suffix": "share",
    },
}


def get_conversion_preset(preset_key: str) -> Optional[Dict[str, Any]]:
    return CONVERSION_PRESETS.get(preset_key)


def get_compression_preset(preset_key: str) -> Optional[Dict[str, Any]]:
    return COMPRESSION_PRESETS.get(preset_key)


def get_download_post_process_preset(preset_key: str) -> Optional[Dict[str, Any]]:
    return DOWNLOAD_POST_PROCESS_PRESETS.get(preset_key)


def build_output_path(input_path: str, suffix: str, target_ext: Optional[str] = None) -> str:
    base, current_ext = os.path.splitext(input_path)
    ext = (target_ext or current_ext.lstrip(".") or "mp4").lstrip(".")
    candidate = f"{base}_{suffix}.{ext}"
    return FileUtils.ensure_unique_filename(candidate)


def build_conversion_job(preset_key: str, input_path: str) -> Optional[Dict[str, Any]]:
    preset = get_conversion_preset(preset_key)
    if not preset:
        return None

    target_format = preset["target_format"]
    suffix = preset.get("suffix", target_format)
    output_path = build_output_path(input_path, suffix, target_format)

    if preset["mode"] == "audio":
        quality = str(preset.get("audio_quality", "192k")).replace("k", "")
        return {
            "action": "extract_audio",
            "label": preset["label"],
            "output_path": output_path,
            "options": {
                "format": target_format,
                "quality": quality,
            },
        }

    return {
        "action": "convert",
        "label": preset["label"],
        "output_path": output_path,
        "options": {
            "target_ext": target_format,
            "quick_copy": bool(preset.get("quick_copy", False)),
            "vcodec": preset.get("vcodec", "libx264"),
            "acodec": preset.get("acodec", "aac"),
            "preset": preset.get("preset", "medium"),
            "crf": preset.get("crf", 23),
        },
    }


def build_compression_job(preset_key: str, input_path: str) -> Optional[Dict[str, Any]]:
    preset = get_compression_preset(preset_key)
    if not preset:
        return None

    current_ext = os.path.splitext(input_path)[1].lstrip(".") or "mp4"
    output_path = build_output_path(input_path, "compressed", current_ext)
    options: Dict[str, Any] = {
        "preset": preset.get("preset", "medium"),
        "width_scale": preset.get("width_scale", 1.0),
    }

    if preset.get("mode") == "target_size":
        options["target_size"] = preset.get("target_size", 50.0)
    else:
        options["crf"] = preset.get("crf", 23)

    return {
        "action": "compress",
        "label": preset["label"],
        "output_path": output_path,
        "options": options,
    }


def build_post_process_job(preset_key: str, input_path: str) -> Optional[Dict[str, Any]]:
    preset = get_download_post_process_preset(preset_key)
    if not preset:
        return None

    action = preset.get("action", "none")
    if action == "none":
        return {"action": "none", "label": preset["label"], "output_path": input_path, "options": {}}

    if action == "convert":
        return build_conversion_job(preset["conversion_preset"], input_path)

    if action == "compress":
        job = build_compression_job(preset["compression_preset"], input_path)
        if job and preset.get("suffix"):
            ext = os.path.splitext(job["output_path"])[1].lstrip(".")
            job["output_path"] = build_output_path(input_path, preset["suffix"], ext)
        return job

    return None
