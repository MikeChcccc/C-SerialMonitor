from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QLinearGradient

# 主题颜色配置 - 支持多种主题
THEMES = {
    "粉色": {
        "PRIMARY": "#F8C8DC",  # 浅粉色
        "SECONDARY": "#FF69B4",  # 热粉色
        "ACCENT": "#FF1493",  # 深粉色
        "LIGHT": "#FFF0F5",  # 薰衣草 blush
        "DARK": "#C71585",  # 紫红色
        "SUCCESS": "#98FB98",  # 浅绿色
        "WARNING": "#FFD700",  # 金色
        "INFO": "#87CEFA",  # 浅蓝色
        "SEND_AREA": "#FFE4E6",  # 非常浅的粉色
        "RECEIVE_AREA": "#FFF0F5",  # 薰衣草 blush
        "GROUP_BOX": "#FFB6C1"  # 浅粉色
    },
    "青色": {
        "PRIMARY": "#E0FFFF",  # 浅青色
        "SECONDARY": "#00CED1",  # 中青色
        "ACCENT": "#008B8B",  # 深青色
        "LIGHT": "#E0FFFF",  # 浅青色
        "DARK": "#008B8B",  # 深青色
        "SUCCESS": "#98FB98",  # 浅绿色
        "WARNING": "#FFD700",  # 金色
        "INFO": "#87CEFA",  # 浅蓝色
        "SEND_AREA": "#E0FFFF",  # 浅青色
        "RECEIVE_AREA": "#E0FFFF",  # 浅青色
        "GROUP_BOX": "#AFEEEE"  # 淡青色
    },
    "蓝色": {
        "PRIMARY": "#E6EEF7",  # 浅蓝色
        "SECONDARY": "#4682B4",  # 钢蓝色
        "ACCENT": "#1E3A8A",  # 深蓝色
        "LIGHT": "#F0F8FF",  # 爱丽丝蓝
        "DARK": "#0A2463",  # 暗蓝色
        "SUCCESS": "#98FB98",  # 浅绿色
        "WARNING": "#FFD700",  # 金色
        "INFO": "#87CEFA",  # 浅蓝色
        "SEND_AREA": "#E6EEF7",  # 浅蓝色
        "RECEIVE_AREA": "#F0F8FF",  # 爱丽丝蓝
        "GROUP_BOX": "#B0C4DE"  # 亮钢蓝
    },
    "紫色": {
        "PRIMARY": "#E6E6FA",  # 淡紫色
        "SECONDARY": "#9370DB",  # 中紫色
        "ACCENT": "#483D8B",  # 深紫色
        "LIGHT": "#F8F8FF",  # 幽灵白
        "DARK": "#483D8B",  # 深紫色
        "SUCCESS": "#98FB98",  # 浅绿色
        "WARNING": "#FFD700",  # 金色
        "INFO": "#87CEFA",  # 浅蓝色
        "SEND_AREA": "#E6E6FA",  # 淡紫色
        "RECEIVE_AREA": "#F8F8FF",  # 幽灵白
        "GROUP_BOX": "#DDA0DD"  # plum
    },
    "红色": {
        "PRIMARY": "#FFE4E1",  # 浅红色
        "SECONDARY": "#CD5C5C",  # 印度红
        "ACCENT": "#8B0000",  # 深红色
        "LIGHT": "#FFF5F5",  # 浅红色背景
        "DARK": "#8B0000",  # 深红色
        "SUCCESS": "#98FB98",  # 浅绿色
        "WARNING": "#FFD700",  # 金色
        "INFO": "#87CEFA",  # 浅蓝色
        "SEND_AREA": "#FFE4E1",  # 浅红色
        "RECEIVE_AREA": "#FFF5F5",  # 浅红色背景
        "GROUP_BOX": "#F08080"  # 浅珊瑚色
    },
    "黑色": {
        "PRIMARY": "#2C2C2C",  # 深灰色
        "SECONDARY": "#4A4A4A",  # 中灰色
        "ACCENT": "#708090",  # 石板灰
        "LIGHT": "#1A1A1A",  # 近黑色
        "DARK": "#F0F0F0",  # 浅灰色文字
        "SUCCESS": "#00FF00",  # 绿色
        "WARNING": "#FFFF00",  # 黄色
        "INFO": "#1E90FF",  # 道奇蓝
        "SEND_AREA": "#2C2C2C",  # 深灰色
        "RECEIVE_AREA": "#1A1A1A",  # 近黑色
        "GROUP_BOX": "#4A4A4A"  # 中灰色
    },
    "白色": {
        "PRIMARY": "#FFFFFF",  # 白色
        "SECONDARY": "#F0F0F0",  # 浅灰色
        "ACCENT": "#C0C0C0",  # 银色
        "LIGHT": "#FFFFFF",  # 白色
        "DARK": "#000000",  # 黑色文字
        "SUCCESS": "#008000",  # 绿色
        "WARNING": "#FFA500",  # 橙色
        "INFO": "#0000FF",  # 蓝色
        "SEND_AREA": "#FFFFFF",  # 白色
        "RECEIVE_AREA": "#FFFFFF",  # 白色
        "GROUP_BOX": "#F0F0F0"  # 浅灰色
    },
    "绿色": {
        "PRIMARY": "#E8F5E9",  # 浅绿色
        "SECONDARY": "#4CAF50",  # 中绿色
        "ACCENT": "#2E7D32",  # 深绿色
        "LIGHT": "#F1F8E9",  # 极浅绿色
        "DARK": "#1B5E20",  # 暗绿色
        "SUCCESS": "#81C784",  # 淡绿色
        "WARNING": "#FFD700",  # 金色
        "INFO": "#87CEFA",  # 浅蓝色
        "SEND_AREA": "#E8F5E9",  # 浅绿色
        "RECEIVE_AREA": "#F1F8E9",  # 极浅绿色
        "GROUP_BOX": "#C8E6C9"  # 淡绿色
    }
}

# 当前主题颜色
current_theme = THEMES["蓝色"]

class ThemeManager:
    @staticmethod
    def get_theme(name=None):
        """获取指定主题或当前主题"""
        if name:
            return THEMES.get(name, current_theme)
        return current_theme
    
    @staticmethod
    def set_theme(name):
        """设置当前主题"""
        global current_theme
        if name in THEMES:
            current_theme = THEMES[name]
            return True
        return False
    
    @staticmethod
    def get_all_themes():
        """获取所有主题名称"""
        return list(THEMES.keys())
    
    @staticmethod
    def get_style_sheet():
        """获取当前主题的样式表"""
        return f"""
            QMainWindow {{
                background-color: {current_theme["LIGHT"]};
                color: {current_theme["DARK"]};
            }}
            QLabel {{
                color: {current_theme["DARK"]};
                font-size: 14px;
            }}
            QComboBox, QLineEdit, QSpinBox {{
                background-color: {current_theme["PRIMARY"]};
                color: {current_theme["DARK"]};
                border: 1px solid {current_theme["SECONDARY"]};
                border-radius: 4px;
                padding: 4px;
            }}
            QTextEdit, QListWidget {{
                background-color: {current_theme["PRIMARY"]};
                color: {current_theme["DARK"]};
                border: 1px solid {current_theme["SECONDARY"]};
                border-radius: 4px;
                padding: 6px;
                font-family: Consolas, Monaco, monospace;
                font-size: 14px;
            }}
            QCheckBox {{
                color: {current_theme["DARK"]};
                spacing: 8px;
            }}
            QTabWidget::pane {{
                border: 1px solid {current_theme["SECONDARY"]};
                border-radius: 4px;
                background-color: {current_theme["PRIMARY"]};
            }}
            QTabBar::tab {{
                background-color: {current_theme["PRIMARY"]};
                color: {current_theme["DARK"]};
                padding: 8px 16px;
                border-radius: 4px 4px 0 0;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {current_theme["SECONDARY"]};
                color: white;
                font-weight: bold;
            }}
            QGroupBox {{
                color: {current_theme["DARK"]};
                border: 1px solid {current_theme["SECONDARY"]};
                border-radius: 6px;
                margin-top: 12px;
                padding: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QProgressDialog QLabel {{
                color: {current_theme["DARK"]};
            }}
        """
    
    @staticmethod
    def get_splitter_style():
        """获取分割器的样式"""
        return f"""
            QSplitter::handle {{
                background-color: {current_theme["SECONDARY"]};
                border-radius: 4px;
                margin: 0 4px;
            }}
            QSplitter::handle:hover {{
                background-color: {current_theme["ACCENT"]};
            }}
        """
    
    @staticmethod
    def get_receive_text_style():
        """获取接收文本区域的样式"""
        return f"""
            QTextEdit {{
                background-color: {current_theme["RECEIVE_AREA"]};
                color: {current_theme["DARK"]};
                border: 1px solid {current_theme["INFO"]};
                border-radius: 6px;
                padding: 8px;
                font-family: Consolas, Monaco, monospace;
                font-size: 14px;
                selection-background-color: {current_theme["SECONDARY"]};
            }}
        """
    
    @staticmethod
    def get_send_text_style():
        """获取发送文本区域的样式"""
        return f"""
            QTextEdit {{
                background-color: {current_theme["SEND_AREA"]};
                color: {current_theme["DARK"]};
                border: 1px solid {current_theme["SUCCESS"]};
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                font-family: Consolas, Monaco, monospace;
            }}
            QTextEdit:focus {{
                border: 1px solid {current_theme["ACCENT"]};
                outline: none;
            }}
        """
    
    @staticmethod
    def get_connect_button_style(is_connected):
        """获取连接按钮的样式"""
        if is_connected:
            normal_style = f"""
                QPushButton {{
                    background-color: {current_theme["ACCENT"]};
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    border: none;
                }}
            """
            hover_style = f"""
                QPushButton {{
                    background-color: {current_theme["SUCCESS"]};
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    border: none;

                }}
            """
        else:
            normal_style = f"""
                QPushButton {{
                    background-color: {current_theme["SUCCESS"]};
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    border: none;
                }}
            """
            hover_style = f"""
                QPushButton {{
                    background-color: {current_theme["ACCENT"]};
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    border: none;

                }}
            """
        
        return normal_style, hover_style