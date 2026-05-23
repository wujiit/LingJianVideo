"""
Settings widget for application configuration
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.config_manager import ConfigManager


class SettingsWidget(QWidget):
    """Widget for application settings."""

    settings_changed = Signal()

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "常规")
        tabs.addTab(self._create_download_tab(), "下载")
        tabs.addTab(self._create_network_tab(), "网络")
        tabs.addTab(self._create_advanced_tab(), "高级")
        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reset_btn = QPushButton("恢复默认")
        reset_btn.setObjectName("ghost")
        reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(reset_btn)

        save_btn = QPushButton("保存设置")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("选择下载目录...")
        path_layout.addWidget(self.path_input)

        browse_btn = QPushButton("浏览...")
        browse_btn.setObjectName("ghost")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)
        layout.addRow("下载目录:", path_layout)

        self.naming_combo = QComboBox()
        self.naming_combo.addItems(
            [
                "{title}",
                "{title} - {author}",
                "{author} - {title}",
                "{date} - {title}",
                "{id} - {title}",
            ]
        )
        self.naming_combo.setEditable(True)
        layout.addRow("命名规则:", self.naming_combo)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv", "webm", "mp3"])
        layout.addRow("默认格式:", self.format_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["深色主题", "浅色主题"])
        layout.addRow("界面主题:", self.theme_combo)

        return widget

    def _create_download_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)

        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(3)
        layout.addRow("同时下载数:", self.concurrent_spin)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["最佳", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p"])
        layout.addRow("默认画质:", self.quality_combo)

        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["H.264 (兼容)", "H.265 (高效)", "VP9", "AV1"])
        layout.addRow("首选编码:", self.codec_combo)

        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["mp3", "m4a", "flac", "wav"])
        layout.addRow("音频格式:", self.audio_format_combo)

        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems(["320 kbps", "256 kbps", "192 kbps", "128 kbps"])
        layout.addRow("音频质量:", self.audio_quality_combo)

        return widget

    def _create_network_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)

        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("例如: http://127.0.0.1:7890")
        layout.addRow("代理服务器:", self.proxy_input)

        self.browser_cookies_combo = QComboBox()
        self.browser_cookies_combo.addItems(["不使用", "Chrome", "Edge", "Firefox", "Opera", "Brave", "Vivaldi"])
        layout.addRow("浏览器 Cookies:", self.browser_cookies_combo)

        cookies_layout = QHBoxLayout()
        self.cookies_input = QLineEdit()
        self.cookies_input.setPlaceholderText("选择 cookies.txt 文件...")
        cookies_layout.addWidget(self.cookies_input)

        cookies_btn = QPushButton("浏览...")
        cookies_btn.setObjectName("ghost")
        cookies_btn.clicked.connect(self._browse_cookies)
        cookies_layout.addWidget(cookies_btn)
        layout.addRow("Cookies 文件:", cookies_layout)

        self.ua_input = QLineEdit()
        self.ua_input.setPlaceholderText("默认自动使用 Chrome 最新版伪装")
        layout.addRow("User-Agent:", self.ua_input)

        self.referer_input = QLineEdit()
        self.referer_input.setPlaceholderText("自定义 Referer（可选）")
        layout.addRow("Referer:", self.referer_input)

        self.rate_limit_input = QLineEdit()
        self.rate_limit_input.setPlaceholderText("例如: 1M（留空不限速）")
        layout.addRow("下载限速:", self.rate_limit_input)

        self.request_timeout_spin = QSpinBox()
        self.request_timeout_spin.setRange(5, 600)
        self.request_timeout_spin.setSuffix(" 秒")
        layout.addRow("解析超时:", self.request_timeout_spin)

        self.fragment_retries_spin = QSpinBox()
        self.fragment_retries_spin.setRange(0, 30)
        layout.addRow("分片重试:", self.fragment_retries_spin)

        self.concurrent_fragments_spin = QSpinBox()
        self.concurrent_fragments_spin.setRange(0, 16)
        layout.addRow("分片并发:", self.concurrent_fragments_spin)

        self.sleep_interval_spin = QDoubleSpinBox()
        self.sleep_interval_spin.setRange(0, 60)
        self.sleep_interval_spin.setDecimals(1)
        self.sleep_interval_spin.setSuffix(" 秒")
        layout.addRow("请求间隔:", self.sleep_interval_spin)

        self.max_sleep_interval_spin = QDoubleSpinBox()
        self.max_sleep_interval_spin.setRange(0, 60)
        self.max_sleep_interval_spin.setDecimals(1)
        self.max_sleep_interval_spin.setSuffix(" 秒")
        layout.addRow("最大间隔:", self.max_sleep_interval_spin)

        self.retry_sleep_input = QLineEdit()
        self.retry_sleep_input.setPlaceholderText("linear=1::2 或 fragment:exp=1:20")
        layout.addRow("重试等待:", self.retry_sleep_input)

        return widget

    def _create_advanced_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)

        self.auto_update_check = QCheckBox("自动检查 yt-dlp 更新")
        layout.addRow(self.auto_update_check)

        self.use_aria2_check = QCheckBox("使用 aria2")
        layout.addRow(self.use_aria2_check)

        aria2_path_layout = QHBoxLayout()
        self.aria2_path_input = QLineEdit()
        self.aria2_path_input.setPlaceholderText("aria2c.exe 路径（可选）")
        aria2_path_layout.addWidget(self.aria2_path_input)

        aria2_btn = QPushButton("浏览...")
        aria2_btn.setObjectName("ghost")
        aria2_btn.clicked.connect(self._browse_aria2)
        aria2_path_layout.addWidget(aria2_btn)
        layout.addRow("aria2 路径:", aria2_path_layout)

        self.aria2_args_input = QLineEdit()
        self.aria2_args_input.setPlaceholderText("-x16 -s16 -k1M")
        layout.addRow("aria2 参数:", self.aria2_args_input)

        ffmpeg_path_layout = QHBoxLayout()
        self.ffmpeg_path_input = QLineEdit()
        self.ffmpeg_path_input.setPlaceholderText("使用内置 FFmpeg")
        ffmpeg_path_layout.addWidget(self.ffmpeg_path_input)

        ffmpeg_btn = QPushButton("浏览...")
        ffmpeg_btn.setObjectName("ghost")
        ffmpeg_btn.clicked.connect(self._browse_ffmpeg)
        ffmpeg_path_layout.addWidget(ffmpeg_btn)
        layout.addRow("FFmpeg 路径:", ffmpeg_path_layout)

        self.minimize_tray_check = QCheckBox("最小化到系统托盘")
        layout.addRow(self.minimize_tray_check)

        self.start_minimized_check = QCheckBox("启动时最小化")
        layout.addRow(self.start_minimized_check)

        return widget

    def _browse_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "选择下载目录", self.path_input.text()
        )
        if path:
            self.path_input.setText(path)

    def _browse_cookies(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Cookies 文件", "", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            self.cookies_input.setText(path)

    def _browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 FFmpeg", "", "Executable (*.exe);;All Files (*)"
        )
        if path:
            self.ffmpeg_path_input.setText(path)

    def _browse_aria2(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 aria2c", "", "Executable (*.exe);;All Files (*)"
        )
        if path:
            self.aria2_path_input.setText(path)

    def _load_settings(self):
        self.path_input.setText(self.config.get("download_path", ""))

        naming = self.config.get("naming_rule", "{title}")
        idx = self.naming_combo.findText(naming)
        if idx >= 0:
            self.naming_combo.setCurrentIndex(idx)
        else:
            self.naming_combo.setCurrentText(naming)

        self.format_combo.setCurrentText(self.config.get("output_format", "mp4"))
        self.concurrent_spin.setValue(self.config.get("max_concurrent", 3))
        self.proxy_input.setText(self.config.get("proxy", ""))
        self.rate_limit_input.setText(self.config.get("rate_limit", ""))
        self.request_timeout_spin.setValue(self.config.get("request_timeout", 15))
        self.fragment_retries_spin.setValue(self.config.get("fragment_retries", 3))
        self.concurrent_fragments_spin.setValue(self.config.get("concurrent_fragments", 0))
        self.sleep_interval_spin.setValue(self.config.get("sleep_interval", 0))
        self.max_sleep_interval_spin.setValue(self.config.get("max_sleep_interval", 0))
        self.retry_sleep_input.setText(self.config.get("retry_sleep", ""))
        self.cookies_input.setText(self.config.get("cookies_file", ""))
        self.ua_input.setText(self.config.get("user_agent", ""))
        self.referer_input.setText(self.config.get("referer", ""))

        browser = self.config.get("cookies_from_browser", "none")
        browser_map = {
            "none": "不使用",
            "chrome": "Chrome",
            "edge": "Edge",
            "firefox": "Firefox",
            "opera": "Opera",
            "brave": "Brave",
            "vivaldi": "Vivaldi",
        }
        self.browser_cookies_combo.setCurrentText(browser_map.get(browser, "不使用"))

        self.ffmpeg_path_input.setText(self.config.get("ffmpeg_path", ""))
        self.use_aria2_check.setChecked(self.config.get("use_aria2", False))
        self.aria2_path_input.setText(self.config.get("aria2_path", ""))
        self.aria2_args_input.setText(self.config.get("aria2_args", ""))
        self.auto_update_check.setChecked(self.config.get("auto_update_ytdlp", True))
        self.minimize_tray_check.setChecked(self.config.get("minimize_to_tray", False))
        self.start_minimized_check.setChecked(self.config.get("start_minimized", False))

        theme_map = {"dark": "深色主题", "light": "浅色主题"}
        self.theme_combo.setCurrentText(theme_map.get(self.config.get("theme", "dark"), "深色主题"))

        quality_map = {
            "best": "最佳",
            "2160p": "2160p (4K)",
            "1440p": "1440p (2K)",
            "1080p": "1080p",
            "720p": "720p",
            "480p": "480p",
        }
        self.quality_combo.setCurrentText(
            quality_map.get(self.config.get("default_quality", "best"), "最佳")
        )

        codec_map = {
            "h264": "H.264 (兼容)",
            "h265": "H.265 (高效)",
            "vp9": "VP9",
            "av1": "AV1",
        }
        self.codec_combo.setCurrentText(
            codec_map.get(self.config.get("preferred_codec", "h264"), "H.264 (兼容)")
        )

        self.audio_format_combo.setCurrentText(self.config.get("extract_audio_format", "mp3"))
        audio_quality = self.config.get("audio_quality", "192")
        self.audio_quality_combo.setCurrentText(f"{audio_quality} kbps")

    def _save_settings(self):
        self.config.set("download_path", self.path_input.text(), save=False)
        self.config.set("naming_rule", self.naming_combo.currentText(), save=False)
        self.config.set("output_format", self.format_combo.currentText(), save=False)
        self.config.set("max_concurrent", self.concurrent_spin.value(), save=False)
        self.config.set("proxy", self.proxy_input.text(), save=False)
        self.config.set("rate_limit", self.rate_limit_input.text(), save=False)
        self.config.set("request_timeout", self.request_timeout_spin.value(), save=False)
        self.config.set("fragment_retries", self.fragment_retries_spin.value(), save=False)
        self.config.set("concurrent_fragments", self.concurrent_fragments_spin.value(), save=False)
        self.config.set("sleep_interval", self.sleep_interval_spin.value(), save=False)
        self.config.set("max_sleep_interval", self.max_sleep_interval_spin.value(), save=False)
        self.config.set("retry_sleep", self.retry_sleep_input.text().strip(), save=False)
        self.config.set("cookies_file", self.cookies_input.text(), save=False)
        self.config.set("user_agent", self.ua_input.text(), save=False)
        self.config.set("referer", self.referer_input.text(), save=False)

        browser_map = {
            "不使用": "none",
            "Chrome": "chrome",
            "Edge": "edge",
            "Firefox": "firefox",
            "Opera": "opera",
            "Brave": "brave",
            "Vivaldi": "vivaldi",
        }
        self.config.set(
            "cookies_from_browser",
            browser_map.get(self.browser_cookies_combo.currentText(), "none"),
            save=False,
        )
        self.config.set("ffmpeg_path", self.ffmpeg_path_input.text(), save=False)
        self.config.set("use_aria2", self.use_aria2_check.isChecked(), save=False)
        self.config.set("aria2_path", self.aria2_path_input.text(), save=False)
        self.config.set("aria2_args", self.aria2_args_input.text(), save=False)
        self.config.set("auto_update_ytdlp", self.auto_update_check.isChecked(), save=False)
        self.config.set("minimize_to_tray", self.minimize_tray_check.isChecked(), save=False)
        self.config.set("start_minimized", self.start_minimized_check.isChecked(), save=False)

        theme_map = {"深色主题": "dark", "浅色主题": "light"}
        self.config.set("theme", theme_map.get(self.theme_combo.currentText(), "dark"), save=False)

        quality_map = {
            "最佳": "best",
            "2160p (4K)": "2160p",
            "1440p (2K)": "1440p",
            "1080p": "1080p",
            "720p": "720p",
            "480p": "480p",
        }
        self.config.set(
            "default_quality",
            quality_map.get(self.quality_combo.currentText(), "best"),
            save=False,
        )

        codec_map = {
            "H.264 (兼容)": "h264",
            "H.265 (高效)": "h265",
            "VP9": "vp9",
            "AV1": "av1",
        }
        self.config.set(
            "preferred_codec",
            codec_map.get(self.codec_combo.currentText(), "h264"),
            save=False,
        )

        self.config.set("extract_audio_format", self.audio_format_combo.currentText(), save=False)
        audio_quality = self.audio_quality_combo.currentText().replace(" kbps", "")
        self.config.set("audio_quality", audio_quality, save=False)

        self.config.save()
        self.settings_changed.emit()

    def _reset_settings(self):
        self.config.reset()
        self._load_settings()
