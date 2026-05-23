"""
Update manager for yt-dlp updates
"""
import os
import subprocess
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, QThread, Signal

try:
    import requests
except ImportError:
    requests = None


class UpdateWorker(QThread):
    """Worker thread for checking/applying updates."""

    progress = Signal(str)
    download_progress = Signal(int, int, int)
    finished = Signal(bool, str)

    def __init__(
        self,
        action: str,
        update_dir: Path,
        cached_download_url: str = "",
        cached_latest: str = "",
        cached_asset_name: str = "",
    ):
        super().__init__()
        self.action = action
        self.update_dir = update_dir
        self.cached_download_url = cached_download_url
        self.cached_latest = cached_latest
        self.cached_asset_name = cached_asset_name or "yt-dlp"
        self._cancelled = False
        self.result = None

    def run(self):
        if self.action == "check":
            self._check_update()
        elif self.action == "update":
            self._apply_update()

    def cancel(self):
        """Request graceful cancellation."""
        self._cancelled = True

    def _get_current_version(self) -> str:
        """Get current yt-dlp version from runtime import."""
        try:
            return package_version("yt-dlp")
        except PackageNotFoundError:
            try:
                return package_version("yt_dlp")
            except Exception:
                pass
        except Exception:
            pass

        try:
            import yt_dlp

            return yt_dlp.version.__version__
        except Exception:
            return "unknown"

    def _fetch_release_info(self) -> Dict[str, Any]:
        """Fetch latest yt-dlp release metadata from GitHub."""
        if not requests:
            raise RuntimeError("缺少 requests 依赖，无法在线更新")

        resp = requests.get(
            "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
            timeout=15,
            headers={
                "User-Agent": "VideoDownloadAssistant",
                "Accept": "application/vnd.github+json",
            },
        )

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RuntimeError("检查更新失败：GitHub 接口受限，请稍后重试")
            raise RuntimeError(f"检查更新失败：HTTP {resp.status_code}")

        try:
            data = resp.json()
        except Exception as exc:
            raise RuntimeError(f"检查更新失败：响应解析错误 {exc}") from exc

        latest = data.get("tag_name", "").lstrip("v").strip()
        current = self._get_current_version()
        target_asset = None

        for asset in data.get("assets", []):
            if asset.get("name") == "yt-dlp":
                target_asset = asset
                break

        if not target_asset:
            for asset in data.get("assets", []):
                if asset.get("name") == "yt-dlp.zip":
                    target_asset = asset
                    break

        if not target_asset:
            raise RuntimeError("未找到可用于内核热更新的发布文件")

        download_url = target_asset.get("browser_download_url", "").strip()
        if not download_url:
            raise RuntimeError("更新文件下载地址无效")

        return {
            "current": current,
            "latest": latest,
            "download_url": download_url,
            "asset_name": target_asset.get("name", "yt-dlp"),
        }

    def _is_valid_zipimport_file(self, file_path: Path) -> bool:
        """
        Validate that the downloaded file looks like a zip/zipapp file.
        yt-dlp binary may contain a shebang then PK header.
        """
        try:
            with open(file_path, "rb") as fh:
                head = fh.read(8192)
            return b"PK\x03\x04" in head
        except Exception:
            return False

    def _check_update(self):
        """Check for yt-dlp updates."""
        try:
            self.progress.emit("正在检查更新...")
            info = self._fetch_release_info()

            has_update = bool(info["latest"] and info["latest"] != info["current"])
            self.result = {
                "has_update": has_update,
                "current": info["current"],
                "latest": info["latest"],
                "download_url": info["download_url"],
                "asset_name": info["asset_name"],
            }

            if has_update:
                self.finished.emit(
                    True,
                    f"发现新版本：{info['latest']}（当前：{info['current']}）",
                )
            else:
                self.finished.emit(True, f"已经是最新版本：{info['current']}")
        except Exception as exc:
            self.finished.emit(False, str(exc))

    def _apply_update(self):
        """Apply yt-dlp update by downloading zip/executable."""
        temp_file = None
        try:
            if not requests:
                self.finished.emit(False, "缺少 requests 依赖，无法在线更新")
                return

            self.progress.emit("正在准备更新...")
            self.download_progress.emit(0, 0, 0)

            current = self._get_current_version()
            latest = self.cached_latest
            download_url = self.cached_download_url

            if not download_url:
                info = self._fetch_release_info()
                current = info["current"]
                latest = info["latest"]
                download_url = info["download_url"]
                self.cached_asset_name = info["asset_name"]

            if latest and latest == current:
                self.finished.emit(True, f"已经是最新版本：{current}")
                return

            if not download_url:
                self.finished.emit(False, "无法获取更新下载地址")
                return

            self.progress.emit(f"正在下载 yt-dlp {latest or 'latest'} ...")
            self.update_dir.mkdir(parents=True, exist_ok=True)

            temp_file = self.update_dir / "yt_dlp_latest.zip.tmp"
            target_file = self.update_dir / "yt_dlp_latest.zip"

            with requests.get(
                download_url,
                stream=True,
                timeout=(15, 60),
                headers={"User-Agent": "VideoDownloadAssistant"},
            ) as resp:
                resp.raise_for_status()
                total_size = int(resp.headers.get("content-length", 0) or 0)
                downloaded = 0
                last_percent = -1

                with open(temp_file, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=64 * 1024):
                        if self._cancelled:
                            raise RuntimeError("更新已取消")
                        if not chunk:
                            continue

                        fh.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = min(100, int(downloaded * 100 / total_size))
                            if percent != last_percent:
                                last_percent = percent
                                self.download_progress.emit(percent, downloaded, total_size)
                                self.progress.emit(f"正在下载：{percent}%")
                        else:
                            self.download_progress.emit(-1, downloaded, 0)

            if self._cancelled:
                raise RuntimeError("更新已取消")

            if not temp_file.exists() or temp_file.stat().st_size == 0:
                raise RuntimeError("下载失败：更新文件为空")

            if not self._is_valid_zipimport_file(temp_file):
                raise RuntimeError("下载失败：更新文件校验失败")

            os.replace(temp_file, target_file)
            size = target_file.stat().st_size
            self.download_progress.emit(100, size, size)
            self.finished.emit(True, "更新完成，重启软件后生效")
        except Exception as exc:
            self.finished.emit(False, f"更新失败：{exc}")
        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass


class UpdateManager(QObject):
    """Manager for yt-dlp updates."""

    update_available = Signal(str, str)
    update_progress = Signal(str)
    update_download_progress = Signal(int, int, int)
    update_completed = Signal(bool, str)

    def __init__(self, config_dir: str = None, ytdlp_path: str = None):
        super().__init__()
        app_data = os.environ.get("APPDATA", str(Path.home()))
        self._update_dir = Path(app_data) / "VideoDownloadAssistant" / "updates"
        self._worker: Optional[UpdateWorker] = None
        self._last_check: Optional[datetime] = None
        self._cached_download_url = ""
        self._cached_latest = ""
        self._cached_asset_name = ""

    def set_ytdlp_path(self, ytdlp_path: str):
        pass

    def get_ytdlp_version(self) -> str:
        """Get current yt-dlp version."""
        try:
            return package_version("yt-dlp")
        except PackageNotFoundError:
            try:
                return package_version("yt_dlp")
            except Exception:
                pass
        except Exception:
            pass

        try:
            import yt_dlp

            return yt_dlp.version.__version__
        except Exception:
            return "未安装"

    def get_ffmpeg_version(self, ffmpeg_path: str = "ffmpeg") -> str:
        """Get FFmpeg version."""
        from utils.system_utils import find_ffmpeg_executable

        candidates = []
        if ffmpeg_path and str(ffmpeg_path).lower() != "ffmpeg" and os.path.exists(ffmpeg_path):
            candidates.append(str(ffmpeg_path))

        found_path = find_ffmpeg_executable()
        if found_path not in candidates:
            candidates.append(found_path)

        if "ffmpeg" not in candidates:
            candidates.append("ffmpeg")

        for cmd in candidates:
            try:
                kwargs = {
                    "capture_output": True,
                    "text": True,
                    "encoding": "utf-8",
                    "errors": "ignore",
                    "stdin": subprocess.DEVNULL,
                }

                if os.name == "nt":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                try:
                    result = subprocess.run([cmd, "-version"], **kwargs)
                except Exception:
                    if os.name == "nt":
                        kwargs.pop("creationflags", None)
                        result = subprocess.run([cmd, "-version"], **kwargs)
                    else:
                        raise

                if result.returncode == 0:
                    content = result.stdout + "\n" + result.stderr
                    import re

                    match = re.search(r"ffmpeg version ([^\s,]+)", content)
                    if match:
                        return match.group(1)

                    first_line = result.stdout.split("\n")[0]
                    if len(first_line) > 5:
                        return first_line[:50]

                    return "已安装（无法识别版本）"
            except Exception as exc:
                if cmd != "ffmpeg" and os.path.exists(cmd):
                    return f"已安装（错误：{exc}）"
                continue

        return "未安装"

    def check_update(self, callback: Callable[[bool, str, str], None] = None) -> bool:
        """Check for yt-dlp updates."""
        if self._worker and self._worker.isRunning():
            return False

        worker = UpdateWorker("check", self._update_dir)
        self._worker = worker

        def on_finished(success, message):
            self._last_check = datetime.now()
            if success and worker.result:
                has_update = bool(worker.result.get("has_update"))
                current = worker.result.get("current", "unknown")
                latest = worker.result.get("latest", current)

                self._cached_download_url = worker.result.get("download_url", "")
                self._cached_latest = latest
                self._cached_asset_name = worker.result.get("asset_name", "yt-dlp")

                if has_update:
                    self.update_available.emit(current, latest)
                if callback:
                    callback(has_update, current, latest)
            self.update_completed.emit(success, message)

        worker.progress.connect(self.update_progress.emit)
        worker.download_progress.connect(self.update_download_progress.emit)
        worker.finished.connect(on_finished)
        worker.start()
        return True

    def apply_update(self) -> bool:
        """Apply yt-dlp update."""
        if self._worker and self._worker.isRunning():
            return False

        worker = UpdateWorker(
            "update",
            self._update_dir,
            cached_download_url=self._cached_download_url,
            cached_latest=self._cached_latest,
            cached_asset_name=self._cached_asset_name,
        )
        self._worker = worker

        def on_finished(success, message):
            if success and "更新完成" in message:
                self._cached_download_url = ""
                self._cached_latest = ""
                self._cached_asset_name = ""
            self.update_completed.emit(success, message)

        worker.progress.connect(self.update_progress.emit)
        worker.download_progress.connect(self.update_download_progress.emit)
        worker.finished.connect(on_finished)
        worker.start()
        return True

    def should_check_update(self, interval_days: int = 7) -> bool:
        """Check if update check is due."""
        if not self._last_check:
            return True
        elapsed = datetime.now() - self._last_check
        return elapsed.days >= interval_days

    def cancel(self):
        """Cancel current operation."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()

    def shutdown(self, timeout_ms: int = 1500):
        """Cancel and stop the background update worker."""
        worker = self._worker
        self._worker = None
        if worker is None:
            return

        try:
            worker.cancel()
        except Exception:
            pass

        if worker.isRunning():
            worker.wait(timeout_ms)

        if worker.isRunning():
            try:
                worker.terminate()
            except Exception:
                pass
            worker.wait(500)

        worker.deleteLater()
