# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_submodules


project_dir = Path(SPECPATH).resolve()
src_dir = project_dir / "src"
bin_dir = project_dir / "bin"
images_dir = src_dir / "ui" / "styles" / "images"
icon_file = project_dir / "converted.ico"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

hiddenimports = [
    "yt_dlp",
    "yt_dlp.extractor",
    "yt_dlp.downloader",
    "yt_dlp.postprocessor",
    "PySide6",
    "requests",
]
hiddenimports += collect_submodules("ui")
hiddenimports += collect_submodules("core")
hiddenimports += collect_submodules("controllers")
hiddenimports += collect_submodules("services")
hiddenimports += collect_submodules("utils")


a = Analysis(
    [str(src_dir / "main.py")],
    pathex=[str(src_dir)],
    binaries=[
        (str(bin_dir / "ffmpeg.exe"), "bin"),
        (str(bin_dir / "ffprobe.exe"), "bin"),
    ],
    datas=[
        (str(icon_file), "."),
        (str(images_dir), "images"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="灵简视频助手",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(icon_file)],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="灵简视频助手",
)
