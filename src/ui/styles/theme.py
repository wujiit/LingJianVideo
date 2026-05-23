"""
Dark theme stylesheet for the application
"""
import os
import sys


def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path).replace('\\', '/')

DARK_THEME = f"""
QMainWindow {{
    background-color: #0f1116;
}}

QMainWindow > QWidget {{
    background-color: #0f1116;
}}

QDialog {{
    background-color: #0f1116;
}}

QWidget {{
    background-color: transparent;
    color: #e5e7eb;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}}

QMessageBox {{
    background-color: #0f1116;
    color: #e5e7eb;
    min-width: 400px;
}}

QMessageBox QLabel {{
    color: #e5e7eb;
    min-height: 40px;
}}

QMessageBox QPushButton {{
    background-color: #1b2430;
    border: 1px solid #2a3646;
    border-radius: 6px;
    padding: 6px 16px;
    color: #e2e8f0;
    min-width: 60px;
}}

QMessageBox QPushButton:hover {{
    background-color: #233043;
}}

QMessageBox QPushButton:pressed {{
    background-color: #17212f;
}}

QFrame#AppHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #111827, stop:1 #0b1220);
    border: 1px solid #1f2937;
    border-radius: 12px;
}}

QLabel#AppTitle {{
    font-size: 16px;
    font-weight: 700;
    color: #f8fafc;
}}

QLabel#dialogTitle {{
    font-size: 20px;
    font-weight: 700;
    color: #f8fafc;
}}

QLabel#dialogSubtitle {{
    color: #94a3b8;
}}

QLabel#dialogIcon {{
    font-size: 44px;
}}

QLabel#sectionLabel {{
    color: #cbd5e1;
    font-weight: 600;
}}

QPushButton#headerButton {{
    background-color: #0f172a;
    border: 1px solid #1f2a3a;
    border-radius: 12px;
    padding: 6px 14px;
    color: #e2e8f0;
}}

QPushButton#headerButton:hover {{
    background-color: #1f2937;
}}

QPushButton#headerButton:pressed {{
    background-color: #0b1220;
}}

QGroupBox {{
    background-color: #111827;
    border: 1px solid #1f2a3a;
    border-radius: 12px;
    margin-top: 4px;
    padding: 4px;
    padding-top: 10px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 6px;
    padding: 0 6px;
    border-radius: 6px;
    background-color: #0b1220;
    border: 1px solid #1f2a3a;
    color: #7dd3fc;
    font-weight: 600;
}}

QGroupBox#panelCard {{
    background-color: #0f172a;
    border: 1px solid #1f2a3a;
    border-radius: 12px;
}}

QLabel#status {{
    color: #7dd3fc;
}}

QLabel#error {{
    color: #f87171;
}}

QLabel#success {{
    color: #34d399;
}}

QLabel#warning {{
    color: #fbbf24;
}}

QLabel#muted {{
    color: #94a3b8;
}}

QLabel#videoTitle {{
    font-weight: 600;
    font-size: 14px;
    color: #f1f5f9;
}}

QLabel#thumbnail {{
    background-color: #0f172a;
    border: 1px dashed #2a3646;
    border-radius: 10px;
    color: #64748b;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: #0c1422;
    border: 1px solid #253244;
    border-radius: 12px;
    padding: 7px 10px;
    color: #f8fafc;
    selection-background-color: #7dd3fc;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: #60a5fa;
    background-color: #0b1526;
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: #0b1220;
    color: #64748b;
    border-color: #1f2a3a;
}}

QPushButton {{
    background-color: #1b2430;
    border: 1px solid #2a3646;
    border-radius: 10px;
    padding: 6px 14px;
    color: #e2e8f0;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: #233043;
}}

QPushButton:pressed {{
    background-color: #17212f;
}}

QPushButton:disabled {{
    background-color: #111827;
    color: #64748b;
    border-color: #1f2937;
}}

QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7dd3fc, stop:1 #38bdf8);
    color: #0b1220;
    border: none;
}}

QPushButton#primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #93c5fd, stop:1 #60a5fa);
}}

QPushButton#primary:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #38bdf8, stop:1 #0ea5e9);
}}

QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid #2a3646;
    border-radius: 12px;
    padding: 7px 16px;
    color: #e2e8f0;
}}

QPushButton#ghost:hover {{
    background-color: #1f2937;
}}

QPushButton#danger {{
    background-color: #ef4444;
    border: none;
    color: #0b1220;
}}

QPushButton#danger:hover {{
    background-color: #f87171;
}}

QPushButton#success {{
    background-color: #22c55e;
    border: none;
    color: #0b1220;
}}

QPushButton#success:hover {{
    background-color: #4ade80;
}}

QPushButton#icon {{
    background-color: transparent;
    border: 1px solid transparent;
    padding: 6px;
    border-radius: 10px;
}}

QPushButton#icon:hover {{
    background-color: #1f2937;
    border-color: #233042;
}}

QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QTimeEdit, QDateEdit, QFontComboBox {{
    background-color: #0c1422;
    border: 1px solid #253244;
    border-radius: 12px;
    padding: 6px 32px 6px 10px;
    color: #f8fafc;
    min-height: 18px;
}}

QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateTimeEdit:hover, QTimeEdit:hover, QDateEdit:hover, QFontComboBox:hover {{
    border-color: #60a5fa;
}}

QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus, QTimeEdit:focus, QDateEdit:focus, QFontComboBox:focus {{
    border-color: #60a5fa;
    background-color: #0b1526;
}}

QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateTimeEdit:disabled, QTimeEdit:disabled, QDateEdit:disabled, QFontComboBox:disabled {{
    background-color: #0b1220;
    color: #64748b;
    border-color: #1f2a3a;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid #1f2a3a;
    background-color: #111827;
    border-top-right-radius: 12px;
    border-bottom-right-radius: 12px;
}}

QComboBox::down-arrow {{
    image: url({get_resource_path('images/down_dark.png')});
    width: 16px;
    height: 16px;
    margin-right: 8px;
}}


QComboBox QAbstractItemView {{
    background-color: #0c1422;
    border: 1px solid #253244;
    border-radius: 10px;
    padding: 6px;
    outline: 0;
    selection-background-color: #1f2a3a;
    selection-color: #f8fafc;
    color: #f8fafc;
}}

QComboBox QAbstractItemView::item {{
    padding: 8px 10px;
    border-radius: 6px;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: #1f2a3a;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #1f2a3a;
    background-color: #111827;
    border-top-right-radius: 12px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid #1f2a3a;
    background-color: #111827;
    border-bottom-right-radius: 12px;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({get_resource_path('images/up_dark.png')});
    width: 16px;
    height: 16px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({get_resource_path('images/down_dark.png')});
    width: 16px;
    height: 16px;
}}


QCheckBox, QRadioButton {{
    spacing: 8px;
    color: #e2e8f0;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid #253244;
    background-color: #0c1422;
}}

QRadioButton::indicator {{
    border-radius: 9px;
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: #7dd3fc;
    border-color: #7dd3fc;
}}

QLabel#progressTitle {{
    font-weight: 600;
    color: #f1f5f9;
}}

QLabel#statusIcon {{
    font-size: 16px;
}}

QProgressBar {{
    background-color: #0b1220;
    border: 1px solid #233042;
    border-radius: 6px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7dd3fc, stop:1 #38bdf8);
    border-radius: 6px;
}}

QScrollBar:vertical {{
    background-color: #0b1220;
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: #1f2a3a;
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #2a3646;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: #0b1220;
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: #1f2a3a;
    border-radius: 5px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #2a3646;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QTabWidget::pane {{
    border: 1px solid #1f2a3a;
    border-radius: 16px;
    background-color: #111827;
}}

QTabBar::tab {{
    background-color: #0b1220;
    border: 1px solid transparent;
    padding: 9px 16px;
    margin-right: 8px;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    color: #94a3b8;
}}

QTabBar::tab:selected {{
    background-color: #111827;
    border-color: #1f2a3a;
    color: #7dd3fc;
}}

QTabBar::tab:hover:!selected {{
    background-color: #0f172a;
    color: #e2e8f0;
}}

QTableWidget {{
    background-color: #141a24;
    border: 1px solid #1f2a3a;
    border-radius: 10px;
    gridline-color: #1f2a3a;
}}

QTableWidget::item {{
    padding: 8px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: #1f2937;
}}

QHeaderView::section {{
    background-color: #0f172a;
    border: none;
    padding: 10px;
    color: #7dd3fc;
    font-weight: 600;
}}

QListWidget {{
    background-color: #141a24;
    border: 1px solid #1f2a3a;
    border-radius: 10px;
}}

QListWidget::item {{
    padding: 12px;
    border-bottom: 1px solid #1f2a3a;
}}

QListWidget::item:selected {{
    background-color: #1f2937;
}}

QListWidget::item:hover {{
    background-color: rgba(31, 41, 55, 0.6);
}}

QMenu {{
    background-color: #141a24;
    border: 1px solid #1f2a3a;
    border-radius: 10px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 6px;
}}

QMenu::item:selected {{
    background-color: #1f2937;
}}

QToolTip {{
    background-color: #0f172a;
    border: 1px solid #233042;
    border-radius: 6px;
    padding: 6px;
    color: #e2e8f0;
}}

QStatusBar {{
    background-color: #0f172a;
    border-top: 1px solid #1f2a3a;
}}

QStatusBar::item {{
    border: none;
}}

QFrame#Card, QWidget#progressCard, QWidget#Card {{
    background-color: #0f172a;
    border: 1px solid #1f2a3a;
    border-radius: 12px;
}}

QScrollArea {{
    background-color: #0f172a;
}}

QScrollArea::viewport {{
    background-color: #0f172a;
}}

QScrollArea#queueScroll {{
    border: 1px solid #1f2a3a;
    background-color: #0f172a;
    border-radius: 12px;
}}
"""
def get_light_theme() -> str:
    return LIGHT_THEME

LIGHT_THEME = f"""
QMainWindow {{
    background-color: #eef2f6;
}}

QMainWindow > QWidget {{
    background-color: #eef2f6;
}}

QDialog {{
    background-color: #eef2f6;
}}

QWidget {{
    background-color: transparent;
    color: #0f172a;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
    font-weight: 500;
}}

QMessageBox {{
    background-color: #f7f9fc;
    color: #0f172a;
    min-width: 400px;
}}

QMessageBox QLabel {{
    color: #0f172a;
    min-height: 40px;
}}

QMessageBox QPushButton {{
    background-color: #eef2f6;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 16px;
    color: #0f172a;
    min-width: 60px;
}}

QMessageBox QPushButton:hover {{
    background-color: #e3e8f1;
}}

QMessageBox QPushButton:pressed {{
    background-color: #cbd5e1;
}}

QFrame#AppHeader {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f1f4f8, stop:1 #e6ebf3);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}}

QLabel#AppTitle {{
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
}}

QLabel#dialogTitle {{
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
}}

QLabel#dialogSubtitle {{
    color: #475569;
}}

QLabel#dialogIcon {{
    font-size: 44px;
}}

QLabel#sectionLabel {{
    color: #0f172a;
    font-weight: 700;
}}

QPushButton#headerButton {{
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 6px 14px;
    color: #0f172a;
    font-weight: 700;
}}

QPushButton#headerButton:hover {{
    background-color: #f1f5f9;
}}

QPushButton#headerButton:pressed {{
    background-color: #e2e8f0;
}}

QGroupBox {{
    background-color: #f7f9fc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-top: 4px;
    padding: 4px;
    padding-top: 10px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 6px;
    padding: 0 6px;
    border-radius: 6px;
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    color: #1d4ed8;
    font-weight: 700;
}}

QGroupBox#panelCard {{
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}}

QLabel#status {{
    color: #0284c7;
}}

QLabel#error {{
    color: #dc2626;
}}

QLabel#success {{
    color: #16a34a;
}}

QLabel#warning {{
    color: #d97706;
}}

QLabel#muted {{
    color: #475569;
}}

QLabel#videoTitle {{
    font-weight: 600;
    font-size: 14px;
    color: #0f172a;
}}

QLabel#thumbnail {{
    background-color: #e2e8f0;
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    color: #64748b;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: #ffffff;
    border: 1px solid #b8c6da;
    border-radius: 12px;
    padding: 7px 10px;
    color: #0f172a;
    placeholder-text-color: #64748b;
    selection-background-color: #38bdf8;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: #3b82f6;
    background-color: #ffffff;
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: #f1f5f9;
    color: #94a3b8;
    border-color: #e2e8f0;
}}

QPushButton {{
    background-color: #eef2f6;
    border: 1px solid #c5d0dd;
    border-radius: 10px;
    padding: 6px 14px;
    color: #0f172a;
    font-weight: 700;
}}

QPushButton:hover {{
    background-color: #e3e8f1;
}}

QPushButton:pressed {{
    background-color: #e3e8f1;
}}

QPushButton:disabled {{
    background-color: #e3e8f1;
    color: #94a3b8;
    border-color: #e3e8f1;
}}

QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3b82f6, stop:1 #2563eb);
    color: #f8fafc;
    border: none;
}}

QPushButton#primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #60a5fa, stop:1 #3b82f6);
}}

QPushButton#primary:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2563eb, stop:1 #1d4ed8);
}}

QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid #c7d2e1;
    border-radius: 12px;
    padding: 7px 16px;
    color: #0f172a;
}}

QPushButton#ghost:hover {{
    background-color: #e3e8f1;
}}

QPushButton#danger {{
    background-color: #ef4444;
    border: none;
    color: #f8fafc;
}}

QPushButton#danger:hover {{
    background-color: #f87171;
}}

QPushButton#success {{
    background-color: #22c55e;
    border: none;
    color: #f8fafc;
}}

QPushButton#success:hover {{
    background-color: #4ade80;
}}

QPushButton#icon {{
    background-color: transparent;
    border: 1px solid transparent;
    padding: 6px;
    border-radius: 10px;
}}

QPushButton#icon:hover {{
    background-color: #e3e8f1;
    border-color: #cbd5e1;
}}

QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QTimeEdit, QDateEdit, QFontComboBox {{
    background-color: #ffffff;
    border: 1px solid #b8c6da;
    border-radius: 12px;
    padding: 8px 36px 8px 12px;
    color: #0f172a;
    font-weight: 500;
    min-height: 18px;
}}

QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateTimeEdit:hover, QTimeEdit:hover, QDateEdit:hover, QFontComboBox:hover {{
    border-color: #60a5fa;
}}

QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus, QTimeEdit:focus, QDateEdit:focus, QFontComboBox:focus {{
    border-color: #3b82f6;
    background-color: #ffffff;
}}

QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateTimeEdit:disabled, QTimeEdit:disabled, QDateEdit:disabled, QFontComboBox:disabled {{
    background-color: #f1f5f9;
    color: #94a3b8;
    border-color: #e2e8f0;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid #e2e8f0;
    background-color: #eef2f6;
    border-top-right-radius: 12px;
    border-bottom-right-radius: 12px;
}}

QComboBox::down-arrow {{
    image: url({get_resource_path('images/down_light.png')});
    width: 16px;
    height: 16px;
    margin-right: 8px;
}}


QComboBox QAbstractItemView {{
    background-color: #ffffff;
    border: 1px solid #c7d2e1;
    border-radius: 10px;
    padding: 6px;
    outline: 0;
    selection-background-color: #e2e8f0;
    selection-color: #0f172a;
    color: #0f172a;
}}

QComboBox QAbstractItemView::item {{
    padding: 8px 10px;
    border-radius: 6px;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: #e2e8f0;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #e2e8f0;
    background-color: #eef2f6;
    border-top-right-radius: 12px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid #e2e8f0;
    background-color: #eef2f6;
    border-bottom-right-radius: 12px;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({get_resource_path('images/up_light.png')});
    width: 16px;
    height: 16px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({get_resource_path('images/down_light.png')});
    width: 16px;
    height: 16px;
}}


QCheckBox, QRadioButton {{
    spacing: 8px;
    color: #0f172a;
    font-weight: 600;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid #c7d2e1;
    background-color: #f9fbff;
}}

QRadioButton::indicator {{
    border-radius: 9px;
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: #3b82f6;
    border-color: #3b82f6;
}}

QLabel#progressTitle {{
    font-weight: 600;
    color: #0f172a;
}}

QLabel#statusIcon {{
    font-size: 16px;
}}

QProgressBar {{
    background-color: #e3e8f1;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3b82f6, stop:1 #2563eb);
    border-radius: 6px;
}}

QScrollBar:vertical {{
    background-color: #e3e8f1;
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: #cbd5e1;
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #94a3b8;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: #e3e8f1;
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: #cbd5e1;
    border-radius: 5px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #94a3b8;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QTabWidget::pane {{
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    background-color: #f7f9fc;
}}

QTabBar::tab {{
    background-color: #ffffff;
    border: 1px solid #dbe5ef;
    padding: 9px 16px;
    margin-right: 8px;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    color: #334155;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background-color: #f7f9fc;
    border-color: #e2e8f0;
    color: #2563eb;
    font-weight: 700;
}}

QTabBar::tab:hover:!selected {{
    background-color: #eef2f6;
    color: #0f172a;
}}

QTableWidget {{
    background-color: #f7f9fc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    gridline-color: #e2e8f0;
}}

QTableWidget::item {{
    padding: 8px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: #e3e8f1;
}}

QHeaderView::section {{
    background-color: #eef2f6;
    border: none;
    padding: 10px;
    color: #2563eb;
    font-weight: 600;
}}

QListWidget {{
    background-color: #f7f9fc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}}

QListWidget::item {{
    padding: 12px;
    border-bottom: 1px solid #e2e8f0;
}}

QListWidget::item:selected {{
    background-color: #e3e8f1;
}}

QListWidget::item:hover {{
    background-color: rgba(227, 232, 241, 0.6);
}}

QMenu {{
    background-color: #f7f9fc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 6px;
}}

QMenu::item:selected {{
    background-color: #e3e8f1;
}}

QToolTip {{
    background-color: #f7f9fc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px;
    color: #0f172a;
}}

QStatusBar {{
    background-color: #e9eef5;
    border-top: 1px solid #e2e8f0;
}}

QStatusBar::item {{
    border: none;
}}

QFrame#Card, QWidget#progressCard, QWidget#Card {{
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}}

QScrollArea {{
    background-color: #eef2f6;
}}

QScrollArea::viewport {{
    background-color: #eef2f6;
}}

QScrollArea#queueScroll {{
    border: 1px solid #e2e8f0;
    background-color: #eef2f6;
    border-radius: 12px;
}}
"""


def get_dark_theme() -> str:
    """Get dark theme stylesheet"""
    return DARK_THEME

def get_light_theme() -> str:
    return LIGHT_THEME

def _build_responsive_overrides(metrics) -> str:
    if metrics is None:
        return ""

    base_font = metrics.px(13)
    title_font = metrics.px(16)
    dialog_title_font = metrics.px(20)
    group_padding = metrics.px(4)
    group_padding_top = metrics.px(10)
    group_margin_top = metrics.px(4)
    title_left = metrics.px(6)
    title_pad_v = 0
    title_pad_h = metrics.px(6)
    btn_pad_v = metrics.px(6)
    btn_pad_h = metrics.px(14)
    input_pad_v = metrics.px(6)
    input_pad_h = metrics.px(10)
    combo_pad_right = metrics.px(32)
    tab_pad_v = metrics.px(9)
    tab_pad_h = metrics.px(16)
    tab_gap = metrics.px(8)
    radius_small = metrics.px(6)
    radius_medium = metrics.px(10)
    radius_large = metrics.px(12)

    return f"""
QWidget {{
    font-size: {base_font}px;
}}

QLabel#AppTitle {{
    font-size: {title_font}px;
}}

QLabel#dialogTitle {{
    font-size: {dialog_title_font}px;
}}

QGroupBox {{
    margin-top: {group_margin_top}px;
    padding: {group_padding}px;
    padding-top: {group_padding_top}px;
    border-radius: {radius_large}px;
}}

QGroupBox::title {{
    left: {title_left}px;
    padding: {title_pad_v}px {title_pad_h}px;
    border-radius: {radius_small}px;
}}

QFrame#AppHeader, QFrame#Card, QWidget#progressCard, QWidget#Card, QGroupBox#panelCard {{
    border-radius: {radius_large}px;
}}

QPushButton {{
    padding: {btn_pad_v}px {btn_pad_h}px;
    border-radius: {radius_medium}px;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    padding: {input_pad_v}px {input_pad_h}px;
    border-radius: {radius_large}px;
}}

QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QTimeEdit, QDateEdit, QFontComboBox {{
    padding: {input_pad_v}px {combo_pad_right}px {input_pad_v}px {input_pad_h}px;
    border-radius: {radius_large}px;
}}

QTabBar::tab {{
    padding: {tab_pad_v}px {tab_pad_h}px;
    margin-right: {tab_gap}px;
    border-top-left-radius: {radius_large}px;
    border-top-right-radius: {radius_large}px;
}}
"""


def get_theme(theme: str, metrics=None) -> str:
    base = LIGHT_THEME if theme == 'light' else DARK_THEME
    return base + _build_responsive_overrides(metrics)
