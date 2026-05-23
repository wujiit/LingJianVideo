"""
Disclaimer dialog shown on first run
"""
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from ui.responsive import detect_ui_metrics


DISCLAIMER_TEXT = """
# 免责声明

欢迎使用灵简视频助手。
本软件仅提供技术工具，请仅在合法合规的前提下使用。使用前请认真阅读以下内容：

## 使用原则

- **合法使用**：仅下载您有权访问和使用的内容
- **尊重版权**：请遵守相关法律法规和平台规则
- **个人用途**：下载内容仅供个人学习、研究或备份使用
- **禁止滥用**：不得用于侵权、传播违法内容或其他非法用途

## 责任说明

- 本软件不内置任何侵权内容
- 用户需自行承担使用本软件产生的一切责任
- 开发者不对用户的不当使用行为负责

## 技术说明

- 本软件基于开源项目 yt-dlp 和 FFmpeg 开发
- 软件仅提供下载与处理能力，不对具体内容进行审核
- 请遵守各视频平台的使用条款和服务协议

继续使用本软件，即表示您已阅读、理解并同意以上条款。
"""


class DisclaimerDialog(QDialog):
    """Disclaimer dialog for first run."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用须知")
        metrics = detect_ui_metrics(parent.screen() if parent else None)
        width, height = metrics.bounded_size(600, 500, 460, 420, padding=36)
        self.resize(width, height)
        self.setMinimumSize(metrics.bounded_width(460, 400, 24), metrics.bounded_height(420, 360, 24))
        self.setModal(True)
        self._accepted = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("使用须知与免责声明")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        content = QTextEdit()
        content.setReadOnly(True)
        content.setMarkdown(DISCLAIMER_TEXT)
        layout.addWidget(content, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("primary")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
