# 📥 视频下载助手 (Video Download Assistant)

基于 yt-dlp 和 FFmpeg 的 Windows 视频下载客户端，提供现代化图形界面，面向普通用户。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

## ✨ 功能特点

### 🔗 智能链接解析
- 支持 YouTube、Bilibili、Twitter、TikTok 等 1000+ 网站
- 自动识别单视频和播放列表
- 显示视频标题、作者、时长、缩略图
- 自动获取可用画质和格式

### 📺 智能格式选择
- **推荐模式**：自动选择最佳画质 + 最佳音质
- **自定义模式**：手动选择分辨率、编码格式
- **仅音频模式**：提取 MP3/M4A/FLAC 音频
- 实时预估文件大小

### 📥 下载管理
- 下载队列，支持多任务并发
- 单任务暂停/继续/取消
- 实时速度和剩余时间显示
- 失败自动重试

### ⚙️ 智能策略
- 自动选择兼容性最好的格式
- 文件名自动清洗（移除非法字符）
- 播放列表自动创建文件夹
- 错误信息自动翻译为中文

### 🎨 现代化界面
- 深色主题，护眼设计
- 简洁直观的操作流程
- 高级/简单模式切换
- 详细的状态日志

## 📦 安装使用

### 方式一：下载 exe（推荐）

1. 从 Releases 下载
2. 双击运行，无需安装 Python

### 方式二：从源码运行

```bash
# 克隆项目
git clone https://github.com/your-repo/video-download-assistant.git
cd video-download-assistant

# 安装依赖
pip install -r requirements.txt

# 运行程序
python src/main.py
```

### 方式三：自行打包

```bash
# 安装打包依赖
pip install pyinstaller

# 运行构建脚本
python build/build.py
```

## 🔧 依赖说明

- **Python 3.9+**
- **PySide6** - Qt6 GUI 框架
- **yt-dlp** - 视频下载引擎
- **FFmpeg** - 音视频处理（需要单独安装或使用内置版本）

### FFmpeg 安装

1. 从 [FFmpeg 官网](https://ffmpeg.org/download.html) 下载
2. 解压到任意目录
3. 在软件设置中指定 FFmpeg 路径，或添加到系统 PATH

## 📖 使用说明

### 基本流程

1. **粘贴链接** - 复制视频链接，点击「粘贴」或按回车
2. **选择格式** - 使用推荐设置或自定义画质
3. **开始下载** - 点击「添加到下载队列」
4. **等待完成** - 在队列中查看进度

### 支持的网站

支持 1000+ 网站，包括但不限于：
- YouTube
- Bilibili
- Twitter/X
- 抖音
- 微博
- Instagram
- Facebook
- Vimeo
- 更多...

### 高级功能

- **代理设置**：在设置中配置 HTTP/SOCKS 代理
- **Cookies 支持**：导入浏览器 Cookies 访问登录内容
- **命名规则**：自定义文件命名模板
- **yt-dlp 更新**：一键更新 yt-dlp 到最新版

## 🗂️ 项目结构

```
video_download_assistant/
├── src/
│   ├── main.py                 # 程序入口
│   ├── core/                   # 核心模块
│   │   ├── ytdlp_wrapper.py    # yt-dlp 封装
│   │   ├── ffmpeg_processor.py # FFmpeg 处理
│   │   ├── video_info.py       # 视频信息模型
│   │   └── download_task.py    # 下载任务模型
│   ├── controllers/            # 控制器
│   │   ├── download_manager.py # 下载管理
│   │   └── smart_strategy.py   # 智能策略
│   ├── services/               # 服务
│   │   ├── config_manager.py   # 配置管理
│   │   └── update_manager.py   # 更新管理
│   ├── ui/                     # 用户界面
│   │   ├── main_window.py      # 主窗口
│   │   ├── widgets/            # UI 组件
│   │   ├── dialogs/            # 对话框
│   │   └── styles/             # 主题样式
│   └── utils/                  # 工具模块
│       ├── error_handler.py    # 错误处理
│       ├── file_utils.py       # 文件工具
│       └── logger.py           # 日志系统
├── build/                      # 打包配置
├── requirements.txt            # 依赖列表
└── README.md                   # 说明文档
```

## ⚠️ 免责声明

本软件仅供下载用户有权访问的内容使用。

- 仅下载您拥有合法访问权限的视频
- 尊重内容创作者的版权
- 不得用于任何商业用途
- 下载内容仅供个人学习和研究使用

使用本软件即表示您同意以上条款，并承诺合法使用。

## 📄 许可证

MIT License

## 🙏 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 强大的视频下载引擎
- [FFmpeg](https://ffmpeg.org/) - 音视频处理工具
- [PySide6](https://www.qt.io/qt-for-python) - Qt6 Python 绑定
