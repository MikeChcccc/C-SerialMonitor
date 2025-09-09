from PySide6.QtWidgets import QGroupBox, QPushButton
from PySide6.QtGui import QPainter, QBrush, QLinearGradient, QPen, QColor
from PySide6.QtCore import Qt
from theme_manager import ThemeManager

class GradientGroupBox(QGroupBox):
    """带渐变背景的自定义GroupBox"""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setMinimumHeight(60)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        current_theme = ThemeManager.get_theme()

        # 绘制渐变背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(current_theme["GROUP_BOX"]).lighter(110))
        gradient.setColorAt(1, QColor(current_theme["GROUP_BOX"]).darker(110))
        painter.fillRect(self.rect(), QBrush(gradient))

        # 绘制边框
        pen = QPen(QColor(current_theme["SECONDARY"]), 1)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)

        # 绘制标题
        title_rect = self.rect().adjusted(10, 0, -10, -self.height() + 15)
        font = self.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(current_theme["DARK"])))
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, self.title())
        
    def update(self):
        """重写更新方法，确保主题变化时重绘"""
        super().update()
        self.repaint()  # 强制重绘


class HoverButton(QPushButton):
    """带悬停效果的按钮"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        current_theme = ThemeManager.get_theme()
        self.normal_style = f"""
            QPushButton {{
                background-color: {current_theme["SECONDARY"]};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
        """
        self.hover_style = f"""
            QPushButton {{
                background-color: {current_theme["ACCENT"]};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
        """
        self.disabled_style = f"""
            QPushButton {{
                background-color: #CCCCCC;
                color: #666666;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
        """
        self.setStyleSheet(self.normal_style)

    def enterEvent(self, event):
        if self.isEnabled():
            self.setStyleSheet(self.hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.setStyleSheet(self.normal_style)
        super().leaveEvent(event)

    def update_style(self):
        """更新按钮样式以适应主题变化"""
        current_theme = ThemeManager.get_theme()
        self.normal_style = f"""
            QPushButton {{
                background-color: {current_theme["SECONDARY"]};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
        """
        self.hover_style = f"""
            QPushButton {{
                background-color: {current_theme["ACCENT"]};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
        """
        self.disabled_style = f"""
            QPushButton {{
                background-color: #CCCCCC;
                color: #666666;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
        """
        if self.isEnabled():
            self.setStyleSheet(self.normal_style)
        else:
            self.setStyleSheet(self.disabled_style)