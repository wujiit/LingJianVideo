"""
Main window - 减少空白间距
"""
import hashlib
import os
import time
from PySide6.QtWidgets import (
    QBoxLayout, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStatusBar, QMessageBox, QGroupBox,
    QLineEdit, QGridLayout, QApplication, QProgressBar, QTabWidget, QCompleter,
    QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QThread, Signal, QTimer, QStringListModel
from PySide6.QtGui import QPixmap

from ui.widgets.chinese_line_edit import ChineseLineEdit


from ui.styles.theme import get_theme
from ui.responsive import apply_app_font, detect_ui_metrics
from ui.widgets.format_widget import FormatWidget
from ui.widgets.queue_widget import QueueWidget

from controllers.download_manager import DownloadManager
from services.config_manager import ConfigManager
from services.update_manager import UpdateManager
from core.ffmpeg_processor import FFmpegProcessor
from core.video_info import VideoInfo
from core.ytdlp_wrapper import YtdlpWrapper, CANCELLED_ERROR
from core.download_task import DownloadOptions, TaskStatus
from core.media_presets import build_post_process_job
from utils.file_utils import FileUtils
from utils.error_handler import translate_error
from utils.logger import get_logger


class ParseWorker(QThread):
    finished = Signal(object, str)
    def __init__(self, url, wrapper, options=None):
        super().__init__()
        self.url = url
        self.wrapper = wrapper
        self.options = options
        self._cancelled = False
    
    def cancel(self):
        """Cancel the parsing operation"""
        self._cancelled = True
        self.wrapper.cancel()
    
    def run(self):
        if self._cancelled:
            self.finished.emit(None, CANCELLED_ERROR)
            return
        try:
            result = self.wrapper.get_video_info(self.url, options=self.options)
            if self._cancelled:
                self.finished.emit(None, CANCELLED_ERROR)
            else:
                self.finished.emit(result, "")
        except Exception as e:
            if not self._cancelled:
                self.finished.emit(None, str(e))
            else:
                self.finished.emit(None, CANCELLED_ERROR)


class ThumbnailWorker(QThread):
    result_ready = Signal(bytes, str)

    def __init__(self, url, timeout=5):
        super().__init__()
        self.url = url
        self.timeout = timeout

    def run(self):
        try:
            import requests
            resp = requests.get(self.url, timeout=self.timeout)
            if resp.status_code == 200:
                self.result_ready.emit(resp.content, "")
            else:
                self.result_ready.emit(b"", f"HTTP {resp.status_code}")
        except Exception as e:
            self.result_ready.emit(b"", str(e))


class PostProcessWorker(QThread):
    completed = Signal(str, bool, str, str)
    log_message = Signal(str, str)

    def __init__(self, task_id, input_path, preset_key, delete_source, ffmpeg_path="", parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.input_path = input_path
        self.preset_key = preset_key
        self.delete_source = delete_source
        self.processor = FFmpegProcessor(ffmpeg_path)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        self.processor.cancel()

    def _log(self, message):
        self.log_message.emit(self.task_id, message)

    def run(self):
        try:
            if not os.path.exists(self.input_path):
                self.completed.emit(self.task_id, False, "后处理失败：源文件不存在", self.input_path)
                return

            job = build_post_process_job(self.preset_key, self.input_path)
            if not job or job.get("action") == "none":
                self.completed.emit(self.task_id, True, "无需后处理", self.input_path)
                return

            action = job["action"]
            output_path = job["output_path"]
            options = job.get("options", {})
            label = job.get("label", "后处理")
            self._log(f"开始后处理: {label}")

            if action == "extract_audio":
                success = self.processor.extract_audio(
                    self.input_path,
                    output_path,
                    audio_format=options.get("format", "mp3"),
                    audio_quality=options.get("quality", "192"),
                    progress_callback=None,
                    log_callback=self._log,
                )
            elif action == "convert":
                success = self.processor.convert_format(
                    self.input_path,
                    output_path,
                    options,
                    progress_callback=None,
                    log_callback=self._log,
                )
            elif action == "compress":
                success = self.processor.compress_video(
                    self.input_path,
                    output_path,
                    target_size_mb=options.get("target_size"),
                    crf=options.get("crf"),
                    preset=options.get("preset", "medium"),
                    width_scale=options.get("width_scale"),
                    progress_callback=None,
                    log_callback=self._log,
                )
            else:
                self.completed.emit(self.task_id, False, f"不支持的后处理动作: {action}", self.input_path)
                return

            if self._cancelled:
                if output_path != self.input_path and os.path.exists(output_path):
                    FileUtils.delete_file(output_path)
                self.completed.emit(self.task_id, False, "后处理已取消", self.input_path)
                return

            if not success:
                if output_path != self.input_path and os.path.exists(output_path):
                    FileUtils.delete_file(output_path)
                self.completed.emit(self.task_id, False, f"后处理失败: {label}", self.input_path)
                return

            if self.delete_source and output_path != self.input_path:
                if FileUtils.delete_file(self.input_path):
                    self._log("后处理成功，已删除源文件")
                else:
                    self._log("后处理成功，但源文件删除失败，已保留原文件")

            self.completed.emit(self.task_id, True, f"后处理完成: {label}", output_path)
        except Exception as exc:
            import traceback

            self._log(f"后处理异常: {exc}\n{traceback.format_exc()}")
            self.completed.emit(self.task_id, False, str(exc), self.input_path)


class RuntimeInfoWorker(QThread):
    info_ready = Signal(str, str)

    def __init__(self, ffmpeg_path: str = "", parent=None):
        super().__init__(parent)
        self.ffmpeg_path = ffmpeg_path

    def run(self):
        manager = UpdateManager()
        ytdlp_ver = manager.get_ytdlp_version()
        ffmpeg_ver = manager.get_ffmpeg_version(self.ffmpeg_path)
        self.info_ready.emit(ytdlp_ver, ffmpeg_ver)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._config = ConfigManager()
        self._update_manager = None  # 延迟初始化
        self._download_manager = None  # 延迟初始化
        self._strategy = None
        self._logger = None
        self._wrapper = None  # 延迟初始化
        self._worker = None
        self._current_video_info = None
        self._log_dialog = None
        self._parse_timer = None  # 解析超时计时器
        
        self._parse_request_token = 0
        self._active_parse_token = None
        self._thumbnail_worker = None
        self._thumbnail_request_token = 0
        self._active_thumbnail_token = None
        self._thumbnail_cache = {}
        self._thumbnail_cache_dir = self._config.config_dir / 'thumbnail_cache'
        self._thumbnail_cache_ttl_seconds = 7 * 24 * 3600
        self._thumbnail_cache_limit = 128
        self._background_workers = set()
        self._parse_status_tone = None
        self._recent_url_model = None
        self._status_worker = None
        self._converter_widget = None
        self._compressor_widget = None
        self._converter_page = None
        self._compressor_page = None
        self._post_process_workers = {}
        self._is_closing = False
        self._screen_tracking_bound = False
        self._ui_metrics = detect_ui_metrics()
        self._responsive_ready = False
        self._setup_ui()
        self._connect_signals()
        self._apply_ui_metrics(initial=True)
        self._apply_theme()
        
        # 先显示窗口，再后台初始化
        QTimer.singleShot(0, self._delayed_init)

    def _ensure_logger(self):
        if self._logger is None:
            self._logger = get_logger()
        return self._logger

    def _ensure_strategy(self):
        if self._strategy is None:
            from controllers.smart_strategy import SmartStrategy
            self._strategy = SmartStrategy()
        return self._strategy
    
    def _delayed_init(self):
        """延迟初始化耗时组件，分段让出事件循环。"""
        if self._is_closing:
            return
        self._wrapper = YtdlpWrapper()
        QTimer.singleShot(0, self._continue_deferred_init)

    def _continue_deferred_init(self):
        if self._is_closing:
            return

        self._setup_recent_url_completer()
        self._update_manager = UpdateManager(ytdlp_path=self._config.get('ytdlp_path', '').strip())
        QTimer.singleShot(0, self._finish_deferred_init)

    def _finish_deferred_init(self):
        if self._is_closing:
            return

        self._download_manager = DownloadManager(self._config.get_ffmpeg_path())
        
        # 连接download_manager信号
        self._download_manager.task_added.connect(self._on_task_added)
        self._download_manager.tasks_updated.connect(self._on_tasks_updated)
        self._download_manager.task_removed.connect(self.queue_widget.remove_task)
        self._download_manager.task_completed.connect(self._on_task_completed)
        
        # 后台更新状态栏版本信息
        self._refresh_runtime_info_async()
        self._ensure_logger().info("视频下载助手已启动")
    
    def _setup_ui(self):
        self.setWindowTitle("灵简视频助手")
        self.resize(1200, 750)
        self.setMinimumSize(1000, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        self._main_layout = QVBoxLayout(central)
        self._main_layout.setSpacing(10)
        self._main_layout.setContentsMargins(12, 12, 12, 12)
        
        # 标题栏
        header = self._create_header()
        self._main_layout.addWidget(header)
        
        # Tab Widget
        self.tabs = QTabWidget()
        self._main_layout.addWidget(self.tabs)
        
        # Download Tab
        download_tab = QWidget()
        self._download_layout = QVBoxLayout(download_tab)
        self._download_layout.setSpacing(10)
        self._download_layout.setContentsMargins(10, 10, 10, 10)
        
        # 视频链接
        url_widget = self._create_url_input()
        self._download_layout.addWidget(url_widget)
        
        # 解析进度条区域
        parse_progress_widget = self._create_parse_progress()
        self._download_layout.addWidget(parse_progress_widget)
        
        # 中间左右布局
        self._middle_layout = QHBoxLayout()
        self._middle_layout.setSpacing(6)
        
        self.info_group = self._create_video_info_panel()
        self._middle_layout.addWidget(self.info_group, 1)
        
        self.format_widget = FormatWidget()
        self._middle_layout.addWidget(self.format_widget, 1)
        
        self._download_layout.addLayout(self._middle_layout)

        # 下载队列
        self.queue_widget = QueueWidget()
        self.queue_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._download_layout.addWidget(self.queue_widget, 1)
        
        self.tabs.addTab(download_tab, "📥 视频下载")
        
        self._converter_page = self._create_lazy_tab_page("切换到此页时再初始化转换工具")
        self.tabs.addTab(self._converter_page, "🔄 视频转换")
        
        self._compressor_page = self._create_lazy_tab_page("切换到此页时再初始化压缩工具")
        self.tabs.addTab(self._compressor_page, "📉 视频压缩")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        self._setup_status_bar()
    
    def _create_header(self):
        self._header = QFrame()
        self._header.setFixedHeight(48)
        self._header.setObjectName("AppHeader")
        
        self._header_layout = QHBoxLayout(self._header)
        self._header_layout.setContentsMargins(12, 0, 12, 0)
        
        self._header_title = QLabel("🎬 灵简视频助手")
        self._header_title.setObjectName("AppTitle")
        self._header_layout.addWidget(self._header_title)
        self._header_layout.addStretch()
        self._header_buttons = []
        
        for text, slot in [("📋日志", self._show_log_dialog), 
                           ("⚙️设置", self._show_settings), 
                           ("ℹ️关于", self._show_about)]:
            btn = QPushButton(text)
            btn.setObjectName("headerButton")
            btn.clicked.connect(slot)
            self._header_buttons.append(btn)
            self._header_layout.addWidget(btn)
        
        return self._header
    
    def _create_url_input(self):
        self._url_widget = QWidget()
        self._url_widget.setObjectName("Card")
        self._url_layout = QHBoxLayout(self._url_widget)
        self._url_layout.setContentsMargins(10, 8, 10, 8)
        self._url_layout.setSpacing(8)
        
        self._url_label = QLabel("🔗 链接:")
        self._url_label.setObjectName("sectionLabel")
        self._url_layout.addWidget(self._url_label)
        
        self.url_input = ChineseLineEdit()
        self.url_input.setPlaceholderText("粘贴视频链接...")
        self.url_input.setFixedHeight(44)
        self.url_input.setMinimumWidth(620)
        self.url_input.returnPressed.connect(self._parse_url)
        self._url_layout.addWidget(self.url_input, 1)
        
        # 按钮加大
        self.paste_btn = QPushButton("📋 粘贴")
        self.paste_btn.setObjectName("ghost")
        self.paste_btn.setFixedSize(96, 40)
        self.paste_btn.clicked.connect(self._paste_from_clipboard)
        self._url_layout.addWidget(self.paste_btn)
        
        self.parse_btn = QPushButton("🔍 解析")
        self.parse_btn.setObjectName("primary")
        self.parse_btn.setFixedSize(96, 40)
        self.parse_btn.clicked.connect(self._parse_url)
        self._url_layout.addWidget(self.parse_btn)
        
        self.clear_btn = QPushButton("✖ 清空")
        self.clear_btn.setObjectName("ghost")
        self.clear_btn.setFixedSize(96, 40)
        self.clear_btn.clicked.connect(self._clear_input)
        self._url_layout.addWidget(self.clear_btn)
        
        self._url_layout.addStretch()
        
        return self._url_widget
    
    def _create_parse_progress(self):
        """创建解析进度条区域"""
        self.parse_progress_widget = QWidget()
        self.parse_progress_widget.setObjectName("Card")
        self._parse_progress_layout = QHBoxLayout(self.parse_progress_widget)
        self._parse_progress_layout.setContentsMargins(10, 8, 10, 8)
        self._parse_progress_layout.setSpacing(8)
        
        # 进度条
        self.parse_progress_bar = QProgressBar()
        self.parse_progress_bar.setRange(0, 0)  # 无限循环模式
        self.parse_progress_bar.setFixedHeight(8)
        self._parse_progress_layout.addWidget(self.parse_progress_bar, 1)
        
        # 状态标签
        self.parse_status_label = QLabel("正在解析视频信息...")
        self.parse_status_label.setObjectName("status")
        self._parse_progress_layout.addWidget(self.parse_status_label)
        
        # 取消按钮
        self.parse_cancel_btn = QPushButton("✖ 取消")
        self.parse_cancel_btn.setObjectName("ghost")
        self.parse_cancel_btn.setFixedSize(96, 32)
        self.parse_cancel_btn.clicked.connect(self._cancel_parse)
        self._parse_progress_layout.addWidget(self.parse_cancel_btn)
        
        # 默认隐藏
        self.parse_progress_widget.setVisible(False)
        
        return self.parse_progress_widget
    
    def _create_video_info_panel(self):
        group = QGroupBox("视频信息")
        group.setObjectName("panelCard")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._info_layout = QVBoxLayout(group)
        self._info_layout.setContentsMargins(10, 8, 10, 10)
        self._info_layout.setSpacing(10)

        self.title_label = QLabel("-")
        self.title_label.setObjectName("videoTitle")
        self.title_label.setWordWrap(True)
        self._info_layout.addWidget(self.title_label)

        self._info_content_row = QHBoxLayout()
        self._info_content_row.setSpacing(12)

        info_widget = QWidget()
        info_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._info_meta_layout = QVBoxLayout(info_widget)
        self._info_meta_layout.setContentsMargins(0, 0, 0, 0)
        self._info_meta_layout.setSpacing(8)

        self._info_grid = QGridLayout()
        self._info_grid.setHorizontalSpacing(16)
        self._info_grid.setVerticalSpacing(8)
        self.author_label = QLabel("作者: -")
        self._info_grid.addWidget(self.author_label, 0, 0)
        self.duration_label = QLabel("时长: -")
        self._info_grid.addWidget(self.duration_label, 0, 1)
        self.site_label = QLabel("来源: -")
        self._info_grid.addWidget(self.site_label, 1, 0)
        self.quality_label = QLabel("画质: -")
        self._info_grid.addWidget(self.quality_label, 1, 1)
        self.size_label = QLabel("大小: -")
        self._info_grid.addWidget(self.size_label, 2, 0)
        self._info_meta_layout.addLayout(self._info_grid)

        self._info_content_row.addWidget(info_widget, 1)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(300, 170)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setObjectName("thumbnail")
        self.thumbnail_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._info_content_row.addWidget(self.thumbnail_label, 0, Qt.AlignTop | Qt.AlignRight)

        self._info_layout.addLayout(self._info_content_row)
        self._set_thumbnail_placeholder("等待解析...")

        return group

    def _create_lazy_tab_page(self, message):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("muted")
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()
        return page

    def _mount_lazy_tab_content(self, page, widget):
        layout = page.layout()
        while layout.count():
            item = layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.deleteLater()
        layout.addWidget(widget)
        if hasattr(widget, "apply_ui_metrics"):
            widget.apply_ui_metrics(self._ui_metrics)

    def _ensure_lazy_tab_loaded(self, tab_name):
        if tab_name == 'converter':
            if self._converter_widget is not None:
                return
            from ui.widgets.converter_widget import ConverterWidget
            self._converter_widget = ConverterWidget(self._config)
            self._mount_lazy_tab_content(self._converter_page, self._converter_widget)
            return

        if tab_name == 'compressor':
            if self._compressor_widget is not None:
                return
            from ui.widgets.compressor_widget import CompressorWidget
            self._compressor_widget = CompressorWidget(self._config)
            self._mount_lazy_tab_content(self._compressor_page, self._compressor_widget)

    def _on_tab_changed(self, index):
        if index == self.tabs.indexOf(self._converter_page):
            self._ensure_lazy_tab_loaded('converter')
        elif index == self.tabs.indexOf(self._compressor_page):
            self._ensure_lazy_tab_loaded('compressor')

    def _current_screen(self):
        handle = self.windowHandle()
        if handle is not None and handle.screen() is not None:
            return handle.screen()
        return QApplication.primaryScreen()

    def _bind_screen_tracking(self):
        if self._screen_tracking_bound:
            return

        handle = self.windowHandle()
        if handle is None:
            QTimer.singleShot(80, self._bind_screen_tracking)
            return

        handle.screenChanged.connect(self._on_screen_changed)
        self._screen_tracking_bound = True
        self._refresh_ui_metrics()

    def _on_screen_changed(self, screen):
        self._refresh_ui_metrics(screen)

    def _refresh_ui_metrics(self, screen=None):
        metrics = detect_ui_metrics(screen or self._current_screen())
        if metrics == self._ui_metrics and self._responsive_ready:
            self._update_adaptive_layout_mode()
            return

        self._ui_metrics = metrics
        self._apply_ui_metrics(initial=not self._responsive_ready)
        self._apply_theme()
        self._responsive_ready = True

    def _apply_ui_metrics(self, initial=False):
        metrics = self._ui_metrics
        app = QApplication.instance()
        apply_app_font(app, metrics)

        min_width, min_height = metrics.bounded_size(920, 560, 760, 500, padding=24)
        pref_width, pref_height = metrics.bounded_size(1200, 750, 980, 620, padding=56)
        self.setMinimumSize(min_width, min_height)

        if initial:
            self.resize(pref_width, pref_height)
        else:
            max_width = max(min_width, metrics.available_width - metrics.px(16))
            max_height = max(min_height, metrics.available_height - metrics.px(16))
            self.resize(
                min(max(self.width(), min_width), max_width),
                min(max(self.height(), min_height), max_height),
            )

        outer_margin = metrics.choose(2, 4, 6)
        section_margin = metrics.choose(2, 4, 6)
        section_spacing = metrics.choose(3, 4, 6)
        compact_button_width = metrics.choose(82, 92, 104)
        compact_button_height = metrics.choose(36, 40, 42)

        self._main_layout.setSpacing(metrics.choose(4, 6, 8))
        self._main_layout.setContentsMargins(
            outer_margin, outer_margin, outer_margin, outer_margin
        )
        self._download_layout.setSpacing(section_spacing)
        self._download_layout.setContentsMargins(
            section_margin, section_margin, section_margin, section_margin
        )
        self._middle_layout.setSpacing(metrics.choose(3, 4, 6))

        self._header.setFixedHeight(metrics.choose(44, 48, 52))
        self._header_layout.setContentsMargins(
            metrics.choose(10, 12, 14), 0, metrics.choose(10, 12, 14), 0
        )

        self._url_layout.setContentsMargins(
            section_margin, metrics.choose(4, 6, 8), section_margin, metrics.choose(4, 6, 8)
        )
        self._url_layout.setSpacing(metrics.choose(4, 6, 8))
        self.url_input.setFixedHeight(metrics.choose(40, 44, 46))
        self.url_input.setMinimumWidth(metrics.bounded_width(620, 360, padding=140))
        self.paste_btn.setFixedSize(compact_button_width, compact_button_height)
        self.parse_btn.setFixedSize(compact_button_width, compact_button_height)
        self.clear_btn.setFixedSize(compact_button_width, compact_button_height)

        self._parse_progress_layout.setContentsMargins(
            section_margin, metrics.choose(4, 6, 8), section_margin, metrics.choose(4, 6, 8)
        )
        self._parse_progress_layout.setSpacing(metrics.choose(4, 6, 8))
        self.parse_progress_bar.setFixedHeight(metrics.choose(6, 8, 8))
        self.parse_cancel_btn.setFixedSize(
            metrics.choose(84, 96, 104), metrics.choose(30, 32, 34)
        )

        self._info_layout.setContentsMargins(
            section_margin, metrics.choose(4, 6, 8), section_margin, section_margin
        )
        self._info_layout.setSpacing(metrics.choose(6, 8, 10))
        self._info_meta_layout.setSpacing(metrics.choose(4, 6, 8))
        self._info_grid.setHorizontalSpacing(metrics.choose(8, 12, 14))
        self._info_grid.setVerticalSpacing(metrics.choose(4, 6, 8))
        self._info_content_row.setSpacing(metrics.choose(8, 10, 12))
        thumb_width = metrics.choose(240, 300, 340)
        thumb_height = metrics.choose(136, 170, 192)
        self.thumbnail_label.setFixedSize(thumb_width, thumb_height)

        for page in (self._converter_page, self._compressor_page):
            if page.layout() is not None:
                page.layout().setContentsMargins(
                    metrics.choose(2, 4, 6),
                    metrics.choose(2, 4, 6),
                    metrics.choose(2, 4, 6),
                    metrics.choose(2, 4, 6),
                )

        if hasattr(self.format_widget, "apply_ui_metrics"):
            self.format_widget.apply_ui_metrics(metrics)
        if hasattr(self.queue_widget, "apply_ui_metrics"):
            self.queue_widget.apply_ui_metrics(metrics)
        if self._converter_widget and hasattr(self._converter_widget, "apply_ui_metrics"):
            self._converter_widget.apply_ui_metrics(metrics)
        if self._compressor_widget and hasattr(self._compressor_widget, "apply_ui_metrics"):
            self._compressor_widget.apply_ui_metrics(metrics)

        self._update_adaptive_layout_mode()

    def _update_adaptive_layout_mode(self):
        narrow_threshold = self._ui_metrics.choose(860, 980, 1120)
        direction = QBoxLayout.TopToBottom if self.width() < narrow_threshold else QBoxLayout.LeftToRight
        if self._middle_layout.direction() != direction:
            self._middle_layout.setDirection(direction)
        if self._info_content_row.direction() != QBoxLayout.LeftToRight:
            self._info_content_row.setDirection(QBoxLayout.LeftToRight)
    
    def _setup_status_bar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        self._version_label = QLabel("正在后台读取运行环境...")
        bar.addPermanentWidget(self._version_label)
    
    def _update_status_bar(self):
        """更新状态栏版本信息"""
        if self._update_manager:
            ytdlp_ver = self._update_manager.get_ytdlp_version()
            ffmpeg_path = self._config.get_ffmpeg_path()
            ffmpeg_ver = self._update_manager.get_ffmpeg_version(ffmpeg_path)
            self._version_label.setText(f"yt-dlp: {ytdlp_ver} | FFmpeg: {ffmpeg_ver}")

    def _refresh_runtime_info_async(self):
        if self._status_worker and self._status_worker.isRunning():
            return
        ffmpeg_path = self._config.get_ffmpeg_path()
        worker = RuntimeInfoWorker(ffmpeg_path, self)
        self._status_worker = worker
        self._retain_background_worker(worker)
        worker.info_ready.connect(self._on_runtime_info_ready)
        worker.finished.connect(lambda worker=worker: self._release_background_worker(worker))
        worker.start()

    def _on_runtime_info_ready(self, ytdlp_ver, ffmpeg_ver):
        self._version_label.setText(f"yt-dlp: {ytdlp_ver} | FFmpeg: {ffmpeg_ver}")
    
    def _connect_signals(self):
        self.format_widget.download_requested.connect(self._on_download_requested)
        self.queue_widget.pause_task.connect(lambda tid: self._download_manager and self._download_manager.pause_task(tid))
        self.queue_widget.resume_task.connect(lambda tid: self._download_manager and self._download_manager.resume_task(tid))
        self.queue_widget.cancel_task.connect(self._on_cancel_task_requested)
        self.queue_widget.retry_task.connect(lambda tid: self._download_manager and self._download_manager.retry_task(tid))
        self.queue_widget.clear_completed.connect(self._on_clear_completed)
        self.queue_widget.open_folder.connect(self._on_open_folder)
        self._config.config_changed.connect(self._on_config_changed)

    def _on_cancel_task_requested(self, tid):
        self._cancel_post_process_task(tid)
        if self._download_manager:
            self._download_manager.cancel_task(tid)
    
    def _apply_theme(self):
        theme = self._config.get('theme', 'dark')
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme(theme, self._ui_metrics))
        else:
            self.setStyleSheet(get_theme(theme, self._ui_metrics))
        if self.parse_status_label:
            self._parse_status_tone = None
            self._set_parse_status(self.parse_status_label.text(), self.parse_status_label.objectName() or "status")
    
    def _paste_from_clipboard(self):
        text = QApplication.clipboard().text()
        if text:
            self.url_input.setText(text)
            if text.startswith('http'):
                self._parse_url()
    
    def _parse_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        if not self._wrapper:
            self._ensure_logger().warning("正在初始化，请稍候...")
            return
        if not self._wrapper.validate_url(url):
            self._ensure_logger().error("链接格式无效")
            return
        
        default_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        timeout_seconds = self._config.get('request_timeout', 15)
        try:
            timeout_seconds = int(timeout_seconds)
        except Exception:
            timeout_seconds = 15
        timeout_seconds = max(5, min(timeout_seconds, 600))
        
        parse_options = {
            'user_agent': self._config.get('user_agent') or default_ua,
            'proxy': self._config.get('proxy'),
            'referer': self._config.get('referer'),
            'cookies_from_browser': self._config.get('cookies_from_browser'),
            'cookies_file': self._config.get('cookies_file'),
            'socket_timeout': timeout_seconds,
        }
        
        parse_options = {k: v for k, v in parse_options.items() if v and v != 'none'}
        self._abort_parse_request()
        self._active_thumbnail_token = None
            
        self.parse_btn.setEnabled(False)
        
        self._set_parse_status("正在解析视频信息...", "status")
        self.parse_progress_widget.setVisible(True)
        
        # 启动超时计时器
        self._parse_timer = QTimer(self)
        self._parse_timer.setSingleShot(True)
        self._parse_timer.timeout.connect(self._on_parse_timeout)
        self._parse_timer.start(timeout_seconds * 1000)
        
        self._parse_request_token += 1
        token = self._parse_request_token
        self._active_parse_token = token

        worker = ParseWorker(url, self._wrapper, parse_options)
        self._worker = worker
        self._retain_background_worker(worker)
        worker.finished.connect(lambda info, error, token=token: self._on_parse_finished(token, info, error))
        worker.finished.connect(lambda *_args, worker=worker: self._release_background_worker(worker))
        worker.start()
    
    def _on_parse_finished(self, token, info, error):
        # 停止超时计时器
        if token != self._active_parse_token:
            return

        self._stop_parse_timer()
        self._active_parse_token = None

        self.parse_btn.setEnabled(True)
        
        # 处理取消情况
        if error == CANCELLED_ERROR:
            self._show_parse_feedback("已终止当前解析", "warning", 2000)
            self._ensure_logger().info("解析已取消")
            return
        
        if error or not info:
            self._set_parse_status(f"解析失败: {translate_error(error) if error else '未知'}", "error")
            self._ensure_logger().error(f"解析失败: {translate_error(error) if error else '未知'}")
            # 3秒后隐藏进度条区域
            self._hide_parse_feedback_later(self._parse_request_token, 3000)
            return
        
        # 解析成功，隐藏进度条
        self.parse_progress_widget.setVisible(False)
        self._current_video_info = info
        self._remember_recent_url(info.url or self.url_input.text().strip())
        self._update_video_info(info)
        self.format_widget.set_video_info(info)
        self._ensure_logger().info(f"解析成功: {info.title[:30]}...")
    
    def _on_parse_timeout(self):
        """解析超时处理"""
        self._abort_parse_request()
        self.parse_btn.setEnabled(True)
        self._show_parse_feedback("解析超时，已终止当前解析", "error", 3000)
        self._ensure_logger().warning("解析超时，请检查链接或网络后重试")
    
    def _cancel_parse(self):
        """用户手动取消解析"""
        self._abort_parse_request()
        self.parse_btn.setEnabled(True)
        self._show_parse_feedback("已终止当前解析", "warning", 2000)
        self._ensure_logger().info("解析已取消")
    
    def _update_video_info(self, info):
        self.title_label.setText(info.title[:50] + "..." if len(info.title) > 50 else info.title)
        self.author_label.setText(f"作者: {info.author or '-'}")
        self.duration_label.setText(f"时长: {info.duration_str}")
        self.site_label.setText(f"来源: {info.site_name}")
        res = info.available_resolutions
        self.quality_label.setText(f"画质: {res[0] if res else '-'}")
        est = info.estimate_size()
        self.size_label.setText(f"大小: ~{est:.1f}MB" if est > 0 else "大小: -")
        if info.thumbnail:
            self._load_thumbnail(info.thumbnail)
        else:
            self._active_thumbnail_token = None
            self._clear_thumbnail()
    
    def _load_thumbnail(self, url):
        self._thumbnail_request_token += 1
        token = self._thumbnail_request_token
        self._active_thumbnail_token = token

        cached = self._thumbnail_cache.get(url)
        if cached is not None:
            self._apply_thumbnail_data(cached)
            return

        disk_cached = self._load_thumbnail_from_disk(url)
        if disk_cached is not None:
            self._cache_thumbnail(url, disk_cached)
            self._apply_thumbnail_data(disk_cached)
            return

        self._clear_thumbnail()
        worker = ThumbnailWorker(url)
        self._thumbnail_worker = worker
        self._retain_background_worker(worker)
        worker.result_ready.connect(
            lambda data, error, token=token, url=url: self._on_thumbnail_loaded(token, url, data, error)
        )
        worker.result_ready.connect(lambda *_args, worker=worker: self._release_background_worker(worker))
        worker.start()
    
    def _clear_input(self):
        self._abort_parse_request()
        self._active_thumbnail_token = None
        self.url_input.clear()
        self._current_video_info = None
        self._set_thumbnail_placeholder("等待解析...")
        self.title_label.setText("-")
        self.author_label.setText("作者: -")
        self.duration_label.setText("时长: -")
        self.site_label.setText("来源: -")
        self.quality_label.setText("画质: -")
        self.size_label.setText("大小: -")
        self.format_widget.reset()
    
    def _show_log_dialog(self):
        from ui.dialogs.log_dialog import LogDialog

        if not self._log_dialog:
            self._log_dialog = LogDialog(self)
        self._log_dialog.show()
        self._log_dialog.raise_()
    
    def _show_about(self):
        from ui.dialogs.about_dialog import AboutDialog

        AboutDialog(self._update_manager, self._config.get_ffmpeg_path(), self).exec()
    
    def _show_settings(self):
        from ui.dialogs.settings_dialog import SettingsDialog

        if SettingsDialog(self._config, self).exec():
            self._apply_theme()
            if self._download_manager:
                self._download_manager.set_max_concurrent(self._config.get('max_concurrent', 3))

    def _on_config_changed(self, key, value):
        if key == 'theme':
            self._apply_theme()
        if key == 'max_concurrent' and self._download_manager:
            self._download_manager.set_max_concurrent(value)
        if key == 'ffmpeg_path' and self._download_manager:
            self._download_manager.set_ffmpeg_path(self._config.get_ffmpeg_path())
            self._refresh_runtime_info_async()
        if key == 'ytdlp_path' and self._update_manager:
            self._update_manager.set_ytdlp_path(str(value).strip())
            self._refresh_runtime_info_async()

    def _refresh_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _set_label_text(self, label, text):
        if label.text() != text:
            label.setText(text)

    def _set_parse_status(self, text, tone):
        self._set_label_text(self.parse_status_label, text)
        if self._parse_status_tone != tone:
            self._parse_status_tone = tone
            self.parse_status_label.setObjectName(tone)
            self._refresh_style(self.parse_status_label)

    def _setup_recent_url_completer(self):
        if self._recent_url_model is not None:
            return
        self._recent_url_model = QStringListModel(self._config.get('recent_urls', []), self)
        completer = QCompleter(self._recent_url_model, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.url_input.setCompleter(completer)

    def _refresh_recent_url_completer(self):
        if self._recent_url_model is None:
            return
        self._recent_url_model.setStringList(self._config.get('recent_urls', []))

    def _remember_recent_url(self, url):
        url = (url or "").strip()
        if not url:
            return
        if self._wrapper and not self._wrapper.validate_url(url):
            return
        self._config.add_recent_url(url)
        self._refresh_recent_url_completer()

    def _show_parse_feedback(self, text, tone, hide_after_ms):
        feedback_token = self._parse_request_token
        self._set_parse_status(text, tone)
        self.parse_progress_widget.setVisible(True)
        self._hide_parse_feedback_later(feedback_token, hide_after_ms)

    def _hide_parse_feedback_later(self, token, delay_ms):
        if delay_ms <= 0:
            self._hide_parse_feedback(token)
            return
        QTimer.singleShot(delay_ms, lambda token=token: self._hide_parse_feedback(token))

    def _hide_parse_feedback(self, token):
        if self._active_parse_token is not None:
            return
        if token != self._parse_request_token:
            return
        self.parse_progress_widget.setVisible(False)

    def _retain_background_worker(self, worker):
        self._background_workers.add(worker)

    def _release_background_worker(self, worker):
        self._background_workers.discard(worker)
        if worker is self._worker:
            self._worker = None
        if worker is self._thumbnail_worker:
            self._thumbnail_worker = None
        if worker is self._status_worker:
            self._status_worker = None
        task_id = getattr(worker, "task_id", None)
        if task_id and self._post_process_workers.get(task_id) is worker:
            self._post_process_workers.pop(task_id, None)
        worker.deleteLater()

    def _disconnect_worker_signals(self, worker):
        if worker is None:
            return

        for signal_name in ("finished", "result_ready", "info_ready", "progress", "status_changed", "log_message", "completed"):
            signal = getattr(worker, signal_name, None)
            if signal is None:
                continue
            try:
                signal.disconnect()
            except (TypeError, RuntimeError):
                pass

    def _shutdown_worker_resources(self, worker, timeout_ms=1200):
        if worker is None:
            return

        wrapper = getattr(worker, "wrapper", None)
        if wrapper is not None and hasattr(wrapper, "shutdown"):
            try:
                wrapper.shutdown()
            except Exception:
                pass

        processor = getattr(worker, "processor", None)
        if processor is not None and hasattr(processor, "shutdown"):
            try:
                processor.shutdown(timeout_ms)
            except Exception:
                pass

    def _stop_parse_timer(self):
        if self._parse_timer:
            self._parse_timer.stop()
            self._parse_timer.deleteLater()
            self._parse_timer = None

    def _abort_parse_request(self):
        self._stop_parse_timer()
        self._active_parse_token = None
        if self._worker:
            if self._worker.isRunning():
                self._worker.cancel()
            self._shutdown_worker_resources(self._worker)
        if self._wrapper and hasattr(self._wrapper, "shutdown"):
            try:
                self._wrapper.shutdown()
            except Exception:
                pass

    def _stop_thread(self, worker, timeout_ms=1200, cancel_first=True):
        if worker is None:
            return

        self._disconnect_worker_signals(worker)

        try:
            if cancel_first and hasattr(worker, "cancel"):
                worker.cancel()
        except Exception:
            pass

        self._shutdown_worker_resources(worker, timeout_ms)

        try:
            worker.requestInterruption()
        except Exception:
            pass

        try:
            worker.quit()
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

        self._shutdown_worker_resources(worker, timeout_ms)

        if not worker.isRunning():
            worker.deleteLater()

    def _shutdown_background_workers(self):
        self._abort_parse_request()
        self._active_thumbnail_token = None
        self.parse_progress_widget.setVisible(False)

        if self._converter_widget and hasattr(self._converter_widget, "shutdown"):
            self._converter_widget.shutdown()

        if self._compressor_widget and hasattr(self._compressor_widget, "shutdown"):
            self._compressor_widget.shutdown()

        for worker in list(self._background_workers):
            timeout_ms = 600 if worker is self._thumbnail_worker else 1500
            self._stop_thread(worker, timeout_ms=timeout_ms)

        self._background_workers.clear()
        self._worker = None
        self._thumbnail_worker = None
        self._status_worker = None
        self._post_process_workers.clear()

    def shutdown(self):
        if self._is_closing:
            return

        self._is_closing = True

        if self._log_dialog:
            try:
                self._log_dialog.close()
            except Exception:
                pass
            self._log_dialog = None

        self._shutdown_background_workers()

        if self._update_manager:
            self._update_manager.shutdown()

        if self._download_manager:
            self._download_manager.shutdown()

        if self._logger and hasattr(self._logger, "shutdown"):
            self._logger.shutdown()

    def _set_thumbnail_style(self, style):
        if self.thumbnail_label.styleSheet() != style:
            self.thumbnail_label.setStyleSheet(style)

    def _set_thumbnail_placeholder(self, text=""):
        self.thumbnail_label.setPixmap(QPixmap())
        self._set_thumbnail_style("")
        self._set_label_text(self.thumbnail_label, text)

    def _clear_thumbnail(self):
        self._set_thumbnail_placeholder()

    def _cache_thumbnail(self, url, data):
        if url in self._thumbnail_cache:
            self._thumbnail_cache.pop(url)
        self._thumbnail_cache[url] = data
        while len(self._thumbnail_cache) > 32:
            oldest = next(iter(self._thumbnail_cache))
            self._thumbnail_cache.pop(oldest)

    def _thumbnail_cache_path(self, url):
        digest = hashlib.sha1(url.encode('utf-8')).hexdigest()
        return self._thumbnail_cache_dir / f"{digest}.img"

    def _load_thumbnail_from_disk(self, url):
        cache_path = self._thumbnail_cache_path(url)
        if not cache_path.exists():
            return None

        try:
            if (time.time() - cache_path.stat().st_mtime) > self._thumbnail_cache_ttl_seconds:
                cache_path.unlink()
                return None
            data = cache_path.read_bytes()
            if not data:
                cache_path.unlink()
                return None
            os.utime(cache_path, None)
            return data
        except Exception:
            return None

    def _save_thumbnail_to_disk(self, url, data):
        if not data:
            return

        cache_path = self._thumbnail_cache_path(url)
        try:
            self._thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
            self._prune_thumbnail_disk_cache()
        except Exception:
            pass

    def _prune_thumbnail_disk_cache(self):
        try:
            files = [path for path in self._thumbnail_cache_dir.iterdir() if path.is_file()]
        except Exception:
            return

        now = time.time()
        valid_files = []
        for path in files:
            try:
                mtime = path.stat().st_mtime
            except Exception:
                continue

            if (now - mtime) > self._thumbnail_cache_ttl_seconds:
                try:
                    path.unlink()
                except Exception:
                    pass
                continue

            valid_files.append((mtime, path))

        valid_files.sort(key=lambda item: item[0], reverse=True)
        for _, path in valid_files[self._thumbnail_cache_limit:]:
            try:
                path.unlink()
            except Exception:
                pass

    def _apply_thumbnail_data(self, data):
        pix = QPixmap()
        if not pix.loadFromData(data):
            return
        target_width = max(1, self.thumbnail_label.width())
        target_height = max(1, self.thumbnail_label.height())
        scaled = pix.scaled(
            target_width,
            target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._set_label_text(self.thumbnail_label, "")
        self.thumbnail_label.setPixmap(scaled)
        self._set_thumbnail_style("padding: 6px; border-radius: 8px;")

    def _on_thumbnail_loaded(self, token, url, data, error):
        if token != self._active_thumbnail_token:
            return
        if not data:
            return
        self._cache_thumbnail(url, data)
        self._save_thumbnail_to_disk(url, data)
        self._apply_thumbnail_data(data)
    
    @Slot(DownloadOptions)
    def _on_download_requested(self, options):
        if not self._current_video_info:
            return
        if not self._download_manager:
            self._ensure_logger().warning("正在初始化，请稍候...")
            return
        info = self._current_video_info
        default_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        options.output_path = self._config.get_download_path()
        options.output_template = self._config.get_output_template()
        options.proxy = self._config.get('proxy') or ""
        options.rate_limit = self._config.get('rate_limit') or ""
        options.cookies_file = self._config.get('cookies_file') or ""
        options.cookies_from_browser = self._config.get('cookies_from_browser') or ""
        options.user_agent = self._config.get('user_agent') or default_ua
        options.referer = self._config.get('referer') or ""
        try:
            options.request_timeout = int(self._config.get('request_timeout', 15))
        except Exception:
            options.request_timeout = 15
        options.fragment_retries = self._config.get('fragment_retries', options.fragment_retries)
        options.sleep_interval = self._config.get('sleep_interval', options.sleep_interval)
        options.max_sleep_interval = self._config.get('max_sleep_interval', options.max_sleep_interval)
        options.retry_sleep = self._config.get('retry_sleep', options.retry_sleep)
        options.concurrent_fragments = self._config.get('concurrent_fragments', options.concurrent_fragments)
        
        if self._config.get('use_aria2', False):
            aria2_path = self._config.get('aria2_path', '').strip()
            options.external_downloader = aria2_path or 'aria2c'
            options.external_downloader_args = self._config.get('aria2_args', '').strip()
        else:
            options.external_downloader = ""
            options.external_downloader_args = ""
        
        if options.cookies_from_browser == 'none':
            options.cookies_from_browser = ""
        
        output_format = self._config.get('output_format', '').lower()
        if not options.extract_audio and options.format_id == 'bestvideo+bestaudio/best':
            if output_format in ('mp4', 'mkv', 'webm'):
                options.merge_format = output_format
        
        if info.is_playlist:
            if QMessageBox.question(self, "播放列表", f"共{info.playlist_count}个视频，全部下载？") == QMessageBox.Yes:
                folder = self._ensure_strategy().suggest_output_folder(info, options.output_path)
                FileUtils.ensure_dir(folder)
                options.output_path = folder
                self.queue_widget.begin_bulk_update()
                try:
                    self._download_manager.add_tasks_from_playlist(info, options)
                finally:
                    self.queue_widget.end_bulk_update()
        else:
            self._download_manager.add_task(info.url, options, info)
        self._clear_input()
    
    @Slot(object)
    def _on_task_added(self, task):
        self.queue_widget.add_task(task)
    
    @Slot(str, object)
    def _on_task_updated(self, tid, task):
        self.queue_widget.update_task(tid, task)

    @Slot(object)
    def _on_tasks_updated(self, tasks):
        self.queue_widget.update_tasks(tasks)
    
    @Slot(str, bool, str)
    def _on_task_completed(self, tid, ok, msg):
        task = self._download_manager.get_task(tid)
        logger = self._ensure_logger()
        if task:
            title = task.title or "未知标题"
            if ok:
                if self._start_post_process(task):
                    logger.info(f"下载完成，开始后处理: {title}")
                    return
                logger.success(f"完成: {title}")
            else:
                raw_error = task.error_message or msg
                translated_error = translate_error(raw_error)
                logger.error(f"失败: {title} - {translated_error}")
                if raw_error:
                    logger.error(f"失败详情: {raw_error}")
        elif msg:
            (logger.success if ok else logger.error)(msg)

    def _start_post_process(self, task):
        if not task or not task.output_file:
            return False

        preset_key = (task.options.post_process_preset or "none").strip()
        if preset_key == "none" or task.id in self._post_process_workers:
            return False

        worker = PostProcessWorker(
            task.id,
            task.output_file,
            preset_key,
            bool(task.options.delete_source_after_post_process),
            self._config.get_ffmpeg_path(),
            self,
        )
        self._post_process_workers[task.id] = worker
        self._retain_background_worker(worker)
        worker.completed.connect(self._on_post_process_finished)
        worker.log_message.connect(self._on_post_process_log)
        worker.finished.connect(lambda worker=worker: self._release_background_worker(worker))

        task.status = TaskStatus.PROCESSING
        task.error_message = ""
        self.queue_widget.update_task(task.id, task)
        worker.start()
        return True

    @Slot(str, str)
    def _on_post_process_log(self, tid, message):
        task = self._download_manager.get_task(tid) if self._download_manager else None
        prefix = task.title if task and task.title else tid
        self._ensure_logger().info(f"[后处理] {prefix}: {message}")

    @Slot(str, bool, str, str)
    def _on_post_process_finished(self, tid, ok, message, output_path):
        task = self._download_manager.get_task(tid) if self._download_manager else None
        logger = self._ensure_logger()
        if not task:
            if message:
                (logger.success if ok else logger.error)(message)
            return

        title = task.title or "未知标题"
        if ok:
            task.status = TaskStatus.COMPLETED
            task.error_message = ""
            if output_path:
                task.output_file = output_path
            logger.success(f"{title} - {message}")
        else:
            if output_path:
                task.output_file = output_path
            task.error_message = message
            if "取消" in message:
                task.status = TaskStatus.CANCELLED
                logger.info(f"{title} - {message}")
            else:
                task.status = TaskStatus.FAILED
                logger.error(f"{title} - {message}")

        self.queue_widget.update_task(tid, task)

    def _cancel_post_process_task(self, tid):
        worker = self._post_process_workers.get(tid)
        if worker is None:
            return
        try:
            worker.cancel()
        except Exception:
            pass
    
    @Slot()
    def _on_clear_completed(self):
        if self._download_manager:
            self._download_manager.clear_completed()
        self.queue_widget.clear_all()
    
    @Slot(str)
    def _on_open_folder(self, tid):
        if self._download_manager:
            task = self._download_manager.get_task(tid)
            FileUtils.open_folder(os.path.dirname(task.output_file) if task and task.output_file else self._config.get_download_path())
        else:
            FileUtils.open_folder(self._config.get_download_path())

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._bind_screen_tracking)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_adaptive_layout_mode()
    
    def closeEvent(self, event):
        if self._is_closing:
            event.accept()
            return

        if self._download_manager and self._download_manager.active_count > 0:
            if QMessageBox.question(self, "退出", f"还有{self._download_manager.active_count}个任务，确定退出？") == QMessageBox.No:
                event.ignore()
                return

        self.shutdown()
        event.accept()

