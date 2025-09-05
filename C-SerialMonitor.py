import sys
import time
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QComboBox, QPushButton,
                               QTextEdit, QLineEdit, QGroupBox, QFormLayout,
                               QCheckBox, QSplitter, QMessageBox, QListWidget,
                               QListWidgetItem, QFileDialog, QSpinBox, QTabWidget, QStyle,
                               QProgressDialog, QMenu, QInputDialog, QStyleOptionGroupBox)
from PySide6.QtCore import (QThread, Signal, Qt, QDateTime, QEvent, QFile,
                            QIODevice, QTimer, QTextStream)
from PySide6.QtGui import (QFont, QTextCursor, QColor, QTextCharFormat,
                           QContextMenuEvent, QAction, QPalette, QLinearGradient,
                           QBrush, QIcon, QPainter, QPen)


# 自定义颜色主题
class ColorTheme:
    PRIMARY = "#2C3E50"
    SECONDARY = "#3498DB"
    ACCENT = "#E74C3C"
    LIGHT = "#ECF0F1"
    DARK = "#1A252F"
    SUCCESS = "#2ECC71"
    WARNING = "#F39C12"
    INFO = "#1ABC9C"
    SEND_AREA = "#2C3E50"
    RECEIVE_AREA = "#ECF0F1"
    GROUP_BOX = "#34495E"


# 常用编码格式映射表
ENCODING_OPTIONS = {
    "UTF-8": "utf-8",
    "GBK (中文)": "gbk",
    "GB2312 (中文)": "gb2312",
    "ANSI (默认)": "latin-1",
    "UTF-16": "utf-16",
    "ASCII": "ascii",
    "GB18030 (扩展中文)": "gb18030"
}

# 编码错误处理方式
ERROR_HANDLING_OPTIONS = {
    "替换错误 (�)": "replace",
    "忽略错误": "ignore",
    "严格模式 (报错)": "strict"
}


class SerialThread(QThread):
    """串口数据接收线程（支持多编码格式）"""
    data_received = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, serial_port, hex_mode=False, encoding="utf-8", error_handling="replace"):
        super().__init__()
        self.serial_port = serial_port
        self.running = False
        self.hex_mode = hex_mode
        self.encoding = encoding  # 接收编码格式
        self.error_handling = error_handling  # 编码错误处理方式

    def run(self):
        self.running = True
        while self.running and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting:
                    # 读取数据
                    data = self.serial_port.read(self.serial_port.in_waiting)

                    if self.hex_mode:
                        # 转换为十六进制字符串
                        text = ' '.join([f'{b:02X}' for b in data]) + ' '
                    else:
                        # 转换为字符串（使用指定编码）
                        text = data.decode(self.encoding, errors=self.error_handling)

                    self.data_received.emit(text)
                self.msleep(10)  # 短暂休眠，减少CPU占用
            except Exception as e:
                self.error_occurred.emit(f"接收错误: {str(e)}")
                break

    def stop(self):
        self.running = False
        self.wait()

    def update_settings(self, hex_mode=None, encoding=None, error_handling=None):
        """更新接收设置（无需重启线程）"""
        if hex_mode is not None:
            self.hex_mode = hex_mode
        if encoding is not None:
            self.encoding = encoding
        if error_handling is not None:
            self.error_handling = error_handling


class FileSendThread(QThread):
    """文件发送线程"""
    progress_updated = Signal(int)
    finished = Signal(bool, str)  # 成功标志, 消息

    def __init__(self, serial_port, file_path, hex_mode=False, encoding="utf-8", chunk_size=1024):
        super().__init__()
        self.serial_port = serial_port
        self.file_path = file_path
        self.hex_mode = hex_mode
        self.encoding = encoding
        self.chunk_size = chunk_size
        self.running = True

    def run(self):
        try:
            # 获取文件大小
            file_size = QFile(self.file_path).size()
            sent_size = 0

            with open(self.file_path, 'rb') as f:
                while self.running and self.serial_port.is_open:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break  # 文件发送完毕

                    if self.hex_mode:
                        # 十六进制模式下需要特殊处理
                        hex_str = chunk.hex()
                        chunk = hex_str.encode(self.encoding)

                    # 发送数据
                    self.serial_port.write(chunk)

                    # 更新进度
                    sent_size += len(chunk)
                    progress = int((sent_size / file_size) * 100) if file_size > 0 else 100
                    self.progress_updated.emit(progress)

                    # 短暂延迟，避免缓冲区溢出
                    time.sleep(0.01)

            if self.running:  # 如果不是被停止的
                self.finished.emit(True, f"文件发送完成，共发送 {sent_size} 字节")
            else:
                self.finished.emit(False, "文件发送已取消")

        except Exception as e:
            self.finished.emit(False, f"文件发送失败: {str(e)}")

    def stop(self):
        self.running = False
        self.wait()


class GradientGroupBox(QGroupBox):
    """带渐变背景的自定义GroupBox"""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setMinimumHeight(60)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制渐变背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(ColorTheme.GROUP_BOX).lighter(110))
        gradient.setColorAt(1, QColor(ColorTheme.GROUP_BOX).darker(110))
        painter.fillRect(self.rect(), QBrush(gradient))

        # 绘制边框
        pen = QPen(QColor(ColorTheme.SECONDARY), 1)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)

        # 绘制标题
        title_rect = self.rect().adjusted(10, 0, -10, -self.height() + 15)
        font = self.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(ColorTheme.LIGHT)))
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, self.title())


class HoverButton(QPushButton):
    """带悬停效果的按钮"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.normal_style = f"""
            QPushButton {{
                background-color: {ColorTheme.SECONDARY};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
        """
        self.hover_style = f"""
            QPushButton {{
                background-color: {ColorTheme.ACCENT};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
        """
        self.setStyleSheet(self.normal_style)

    def enterEvent(self, event):
        self.setStyleSheet(self.hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.normal_style)
        super().leaveEvent(event)


class SerialMonitor(QMainWindow):
    """支持多编码格式的增强版串口监控主窗口"""

    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.serial_thread = None
        self.file_send_thread = None
        self.send_history = []  # 发送历史记录
        self.history_index = -1  # 历史记录索引，用于上下键切换
        self.send_presets = []  # 发送预设
        self.timer = QTimer(self)  # 定时发送计时器
        self.timer.timeout.connect(self.send_data)

        # 设置窗口标题和大小
        self.setWindowTitle("炫酷串口调试工具 🚀")
        self.setGeometry(100, 100, 1200, 800)

        # 设置全局样式
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {ColorTheme.DARK};
                color: {ColorTheme.LIGHT};
            }}
            QLabel {{
                color: {ColorTheme.LIGHT};
                font-size: 14px;
            }}
            QComboBox, QLineEdit, QSpinBox {{
                background-color: {ColorTheme.PRIMARY};
                color: {ColorTheme.LIGHT};
                border: 1px solid {ColorTheme.SECONDARY};
                border-radius: 4px;
                padding: 4px;
            }}
            QTextEdit, QListWidget {{
                background-color: {ColorTheme.PRIMARY};
                color: {ColorTheme.LIGHT};
                border: 1px solid {ColorTheme.SECONDARY};
                border-radius: 4px;
                padding: 6px;
                font-family: Consolas, Monaco, monospace;
                font-size: 14px;
            }}
            QCheckBox {{
                color: {ColorTheme.LIGHT};
                spacing: 8px;
            }}
            QTabWidget::pane {{
                border: 1px solid {ColorTheme.SECONDARY};
                border-radius: 4px;
                background-color: {ColorTheme.PRIMARY};
            }}
            QTabBar::tab {{
                background-color: {ColorTheme.PRIMARY};
                color: {ColorTheme.LIGHT};
                padding: 8px 16px;
                border-radius: 4px 4px 0 0;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {ColorTheme.SECONDARY};
                font-weight: bold;
            }}
            QGroupBox {{
                color: {ColorTheme.LIGHT};
                border: 1px solid {ColorTheme.SECONDARY};
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
                color: {ColorTheme.DARK};
            }}
        """)

        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建串口配置区域
        self.create_config_group(main_layout)

        # 创建数据显示和发送区域的分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {ColorTheme.SECONDARY};
                border-radius: 4px;
                margin: 0 4px;
            }}
            QSplitter::handle:hover {{
                background-color: {ColorTheme.ACCENT};
            }}
        """)

        # 创建接收区域
        self.create_receive_group(splitter)

        # 创建发送区域和预设区域的Tab
        send_tab_widget = QTabWidget()
        send_tab_widget.setStyleSheet(f"""
            QTabWidget::tab-bar {{
                alignment: center;
            }}
        """)
        self.create_send_group(send_tab_widget)
        self.create_preset_group(send_tab_widget)
        splitter.addWidget(send_tab_widget)

        # 设置分割器初始大小和拉伸因子
        splitter.setSizes([500, 350])
        main_layout.addWidget(splitter, 1)  # 添加拉伸因子，使分割器占满空间

        # 初始化串口列表
        self.refresh_serial_ports()
        # 加载发送预设
        self.load_presets()

        # 连接信号和槽
        self.send_text.returnPressed.connect(self.send_data)  # 回车发送

        # 窗口大小变化时重新布局
        self.resizeEvent = self.on_resize

    def on_resize(self, event):
        """窗口大小变化时的处理"""
        # 可以在这里添加自定义的布局调整逻辑
        super().resizeEvent(event)

    def create_config_group(self, parent_layout):
        """创建更丰富的串口配置区域"""
        config_group = GradientGroupBox("串口配置 ⚙️")
        config_layout = QHBoxLayout()
        config_layout.setContentsMargins(10, 10, 10, 10)
        config_layout.setSpacing(15)

        # 左侧布局
        left_layout = QFormLayout()
        left_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        left_layout.setSpacing(10)

        # 串口选择
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(200)
        left_layout.addRow("串口号:", self.port_combo)

        # 波特率选择 - 增加更多常用选项
        self.baudrate_combo = QComboBox()
        baudrates = ["1200", "2400", "4800", "9600", "19200", "38400",
                     "57600", "115200", "230400", "460800", "921600", "1500000"]
        self.baudrate_combo.addItems(baudrates)
        self.baudrate_combo.setCurrentText("115200")  # 默认波特率
        left_layout.addRow("波特率:", self.baudrate_combo)

        # 数据位选择
        self.databits_combo = QComboBox()
        self.databits_combo.addItems(["5", "6", "7", "8"])
        self.databits_combo.setCurrentText("8")
        left_layout.addRow("数据位:", self.databits_combo)

        # 右侧布局
        right_layout = QFormLayout()
        right_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        right_layout.setSpacing(10)

        # 校验位选择
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["无", "奇校验", "偶校验", "标记", "空格"])
        self.parity_combo.setCurrentText("无")
        right_layout.addRow("校验位:", self.parity_combo)

        # 停止位选择
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "1.5", "2"])
        self.stopbits_combo.setCurrentText("1")
        right_layout.addRow("停止位:", self.stopbits_combo)

        # 流控制
        self.flowcontrol_combo = QComboBox()
        self.flowcontrol_combo.addItems(["无", "硬件", "软件"])
        self.flowcontrol_combo.setCurrentText("无")
        right_layout.addRow("流控制:", self.flowcontrol_combo)

        # 控制按钮布局
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)

        self.refresh_btn = HoverButton("刷新端口 🔄")
        self.refresh_btn.clicked.connect(self.refresh_serial_ports)

        self.connect_btn = HoverButton("打开串口 📶")
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ColorTheme.SUCCESS};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {ColorTheme.ACCENT};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
        """)
        self.connect_btn.clicked.connect(self.toggle_connection)

        # 端口信息按钮
        self.port_info_btn = HoverButton("端口信息 ℹ️")
        self.port_info_btn.clicked.connect(self.show_port_info)
        self.port_info_btn.setEnabled(False)

        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.port_info_btn)
        button_layout.addStretch()

        # 添加到配置布局
        config_layout.addLayout(left_layout, 2)
        config_layout.addLayout(right_layout, 2)
        config_layout.addLayout(button_layout, 1)

        config_group.setLayout(config_layout)
        parent_layout.addWidget(config_group)

    def create_receive_group(self, parent):
        """创建增强的数据接收区域（增加编码选择和搜索功能）"""
        receive_group = GradientGroupBox("接收数据 📥")
        receive_layout = QVBoxLayout()
        receive_layout.setContentsMargins(10, 10, 10, 10)
        receive_layout.setSpacing(10)

        # 接收选项（第一行）
        options_layout1 = QHBoxLayout()
        options_layout1.setSpacing(15)

        self.hex_receive_check = QCheckBox("十六进制显示 🧮")
        self.hex_receive_check.stateChanged.connect(self.toggle_hex_receive)

        self.timestamp_check = QCheckBox("显示时间戳 ⏱️")
        self.newline_check = QCheckBox("自动换行 ↩️")
        self.clear_on_send_check = QCheckBox("发送时清空接收区 🗑️")

        options_layout1.addWidget(self.hex_receive_check)
        options_layout1.addWidget(self.timestamp_check)
        options_layout1.addWidget(self.newline_check)
        options_layout1.addWidget(self.clear_on_send_check)
        options_layout1.addStretch()

        # 接收编码选项和搜索功能（第二行）
        options_layout2 = QHBoxLayout()
        options_layout2.setSpacing(15)

        encoding_label = QLabel("接收编码:")
        self.receive_encoding_combo = QComboBox()
        self.receive_encoding_combo.addItems(ENCODING_OPTIONS.keys())
        self.receive_encoding_combo.setCurrentText("UTF-8")
        self.receive_encoding_combo.currentIndexChanged.connect(self.on_receive_encoding_changed)

        error_handling_label = QLabel("错误处理:")
        self.error_handling_combo = QComboBox()
        self.error_handling_combo.addItems(ERROR_HANDLING_OPTIONS.keys())
        self.error_handling_combo.setCurrentText("替换错误 (�)")
        self.error_handling_combo.currentIndexChanged.connect(self.on_error_handling_changed)

        # 搜索功能
        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索内容...")
        self.search_btn = HoverButton("查找下一个 🔍")
        self.search_btn.clicked.connect(self.search_text)
        self.search_case_sensitive = QCheckBox("区分大小写 Aa")

        options_layout2.addWidget(encoding_label)
        options_layout2.addWidget(self.receive_encoding_combo)
        options_layout2.addSpacing(20)
        options_layout2.addWidget(error_handling_label)
        options_layout2.addWidget(self.error_handling_combo)
        options_layout2.addStretch()
        options_layout2.addWidget(search_label)
        options_layout2.addWidget(self.search_input)
        options_layout2.addWidget(self.search_btn)
        options_layout2.addWidget(self.search_case_sensitive)

        # 接收显示区域
        self.receive_text = QTextEdit()
        self.receive_text.setReadOnly(True)  # 只读
        self.receive_text.setLineWrapMode(QTextEdit.WidgetWidth)  # 自动换行
        self.receive_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {ColorTheme.PRIMARY};
                color: {ColorTheme.LIGHT};
                border: 1px solid {ColorTheme.INFO};
                border-radius: 6px;
                padding: 8px;
                font-family: Consolas, Monaco, monospace;
                font-size: 14px;
                selection-background-color: {ColorTheme.SECONDARY};
            }}
        """)
        self.last_search_pos = 0  # 上次搜索位置

        # 统计信息
        stats_layout = QHBoxLayout()
        self.receive_count_label = QLabel("接收字节数: 0")
        self.receive_count_label.setStyleSheet(f"color: {ColorTheme.INFO}; font-weight: bold;")
        stats_layout.addWidget(self.receive_count_label)
        stats_layout.addStretch()

        # 接收区按钮
        btn_layout = QHBoxLayout()
        self.clear_receive_btn = HoverButton("清空接收区 🗑️")
        self.clear_receive_btn.clicked.connect(self.clear_receive_area)

        self.save_receive_btn = HoverButton("保存接收数据 💾")
        self.save_receive_btn.clicked.connect(self.save_received_data)

        btn_layout.addWidget(self.clear_receive_btn)
        btn_layout.addWidget(self.save_receive_btn)

        # 添加到布局
        receive_layout.addLayout(options_layout1)
        receive_layout.addLayout(options_layout2)
        receive_layout.addWidget(self.receive_text, 1)  # 添加拉伸因子
        receive_layout.addLayout(stats_layout)
        receive_layout.addLayout(btn_layout)

        receive_group.setLayout(receive_layout)
        parent.addWidget(receive_group)

    def create_send_group(self, parent):
        """创建增强的数据发送区域（增加编码选择、定时发送和文件发送）"""
        send_widget = QWidget()
        send_layout = QVBoxLayout(send_widget)
        send_layout.setContentsMargins(10, 10, 10, 10)
        send_layout.setSpacing(10)

        # 发送选项
        send_options_layout = QHBoxLayout()
        send_options_layout.setSpacing(15)

        self.hex_send_check = QCheckBox("十六进制发送 🧮")
        self.hex_send_check.stateChanged.connect(self.check_hex_input)

        self.append_newline_check = QCheckBox("自动添加换行 ↩️")

        # 定时发送选项
        self.timed_send_check = QCheckBox("定时发送 ⏱️")
        self.timed_send_check.stateChanged.connect(self.toggle_timed_send)
        self.interval_label = QLabel("间隔(ms):")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 30000)  # 10ms到30秒
        self.interval_spin.setValue(1000)
        self.interval_label.setEnabled(False)
        self.interval_spin.setEnabled(False)

        encoding_label = QLabel("发送编码:")
        self.send_encoding_combo = QComboBox()
        self.send_encoding_combo.addItems(ENCODING_OPTIONS.keys())
        self.send_encoding_combo.setCurrentText("UTF-8")

        send_options_layout.addWidget(self.hex_send_check)
        send_options_layout.addWidget(self.append_newline_check)
        send_options_layout.addSpacing(10)
        send_options_layout.addWidget(self.timed_send_check)
        send_options_layout.addWidget(self.interval_label)
        send_options_layout.addWidget(self.interval_spin)
        send_options_layout.addSpacing(10)
        send_options_layout.addWidget(encoding_label)
        send_options_layout.addWidget(self.send_encoding_combo)
        send_options_layout.addStretch()

        # 文件发送选项
        file_layout = QHBoxLayout()
        file_layout.setSpacing(10)
        self.select_file_btn = HoverButton("选择文件 📂")
        self.select_file_btn.clicked.connect(self.select_file)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.send_file_btn = HoverButton("发送文件 📤")
        self.send_file_btn.clicked.connect(self.send_file)
        self.send_file_btn.setEnabled(False)

        file_layout.addWidget(self.select_file_btn)
        file_layout.addWidget(self.file_path_edit, 1)  # 添加拉伸因子
        file_layout.addWidget(self.send_file_btn)

        # 发送输入框
        self.send_text = QLineEdit()
        self.send_text.setPlaceholderText("请输入要发送的数据...")
        self.send_text.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ColorTheme.PRIMARY};
                color: {ColorTheme.LIGHT};
                border: 1px solid {ColorTheme.SUCCESS};
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }}
        """)
        self.send_text.installEventFilter(self)  # 安装事件过滤器以捕获上下键

        # 添加到预设按钮
        self.add_preset_btn = HoverButton("添加到预设 ⭐")
        self.add_preset_btn.clicked.connect(self.add_to_preset)

        # 发送历史记录
        history_layout = QHBoxLayout()
        history_layout.setSpacing(10)
        history_label = QLabel("发送历史:")
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(80)
        self.history_list.itemClicked.connect(self.on_history_item_clicked)
        self.history_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {ColorTheme.PRIMARY};
                color: {ColorTheme.LIGHT};
                border: 1px solid {ColorTheme.SECONDARY};
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background-color: {ColorTheme.SECONDARY};
                color: white;
            }}
        """)

        history_layout.addWidget(history_label)
        history_layout.addWidget(self.history_list, 1)  # 添加拉伸因子

        # 发送按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.send_btn = HoverButton("发送数据 🚀")
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ColorTheme.SUCCESS};
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 15px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {ColorTheme.ACCENT};
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 15px;
                border: none;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
            QPushButton:disabled {{
                background-color: #7f8c8d;
                color: #bdc3c7;
                box-shadow: none;
            }}
        """)
        self.send_btn.clicked.connect(self.send_data)
        self.send_btn.setEnabled(False)  # 初始禁用

        self.clear_send_btn = HoverButton("清空发送区 🗑️")
        self.clear_send_btn.clicked.connect(lambda: self.send_text.clear())

        self.clear_history_btn = HoverButton("清空历史 🗑️")
        self.clear_history_btn.clicked.connect(self.clear_history)

        button_layout.addWidget(self.send_btn)
        button_layout.addWidget(self.clear_send_btn)
        button_layout.addWidget(self.clear_history_btn)
        button_layout.addWidget(self.add_preset_btn)
        button_layout.addStretch()

        # 添加到布局
        send_layout.addLayout(send_options_layout)
        send_layout.addLayout(file_layout)
        send_layout.addWidget(self.send_text)
        send_layout.addLayout(history_layout)
        send_layout.addLayout(button_layout)

        parent.addTab(send_widget, "即时发送")

    def create_preset_group(self, parent):
        """创建发送预设区域"""
        preset_widget = QWidget()
        preset_layout = QVBoxLayout(preset_widget)
        preset_layout.setContentsMargins(10, 10, 10, 10)
        preset_layout.setSpacing(10)

        # 预设列表
        self.preset_list = QListWidget()
        self.preset_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.preset_list.customContextMenuRequested.connect(self.show_preset_context_menu)
        self.preset_list.itemDoubleClicked.connect(self.use_preset)
        self.preset_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {ColorTheme.PRIMARY};
                color: {ColorTheme.LIGHT};
                border: 1px solid {ColorTheme.INFO};
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background-color: {ColorTheme.INFO};
                color: white;
            }}
        """)

        # 预设按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.save_presets_btn = HoverButton("保存预设 💾")
        self.save_presets_btn.clicked.connect(self.save_presets)

        self.load_presets_btn = HoverButton("加载预设 📂")
        self.load_presets_btn.clicked.connect(self.load_presets_dialog)

        self.clear_presets_btn = HoverButton("清空预设 🗑️")
        self.clear_presets_btn.clicked.connect(self.clear_presets)

        btn_layout.addWidget(self.save_presets_btn)
        btn_layout.addWidget(self.load_presets_btn)
        btn_layout.addWidget(self.clear_presets_btn)
        btn_layout.addStretch()

        preset_label = QLabel("发送预设（双击使用）:")
        preset_label.setStyleSheet(f"color: {ColorTheme.INFO}; font-weight: bold;")

        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.preset_list, 1)  # 添加拉伸因子
        preset_layout.addLayout(btn_layout)

        parent.addTab(preset_widget, "发送预设")

    def eventFilter(self, obj, event):
        """事件过滤器，用于捕获发送框的上下键事件，切换历史记录"""
        if obj is self.send_text and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self.navigate_history(-1)  # 上移
                return True
            elif event.key() == Qt.Key_Down:
                self.navigate_history(1)  # 下移
                return True
        return super().eventFilter(obj, event)

    def navigate_history(self, direction):
        """浏览发送历史记录"""
        if not self.send_history:
            return

        # 更新索引
        new_index = self.history_index + direction

        # 限制索引范围
        if new_index < -1:
            new_index = -1
        elif new_index >= len(self.send_history):
            new_index = len(self.send_history) - 1

        # 更新发送框内容
        if new_index == -1:
            self.send_text.clear()
        else:
            self.send_text.setText(self.send_history[new_index])

        self.history_index = new_index
        # 将光标移动到末尾
        self.send_text.setCursorPosition(len(self.send_text.text()))

    def on_history_item_clicked(self, item):
        """点击历史记录项时，将内容显示到发送框"""
        self.send_text.setText(item.text())
        # 更新历史索引
        self.history_index = self.send_history.index(item.text())

    def add_to_history(self, text):
        """添加内容到发送历史"""
        # 避免重复添加相同内容
        if self.send_history and self.send_history[-1] == text:
            return

        self.send_history.append(text)
        # 限制历史记录数量
        if len(self.send_history) > 50:
            self.send_history.pop(0)

        # 更新历史列表显示
        self.history_list.addItem(text)
        # 确保只显示最近的10条
        while self.history_list.count() > 10:
            self.history_list.takeItem(0)
        # 滚动到最后一项
        self.history_list.scrollToBottom()

    def clear_history(self):
        """清空发送历史"""
        self.send_history.clear()
        self.history_list.clear()
        self.history_index = -1

    def refresh_serial_ports(self):
        """刷新可用串口号列表"""
        current_port = self.port_combo.currentText()
        self.port_combo.clear()

        # 获取所有可用串口
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}")

        # 尝试恢复之前选择的端口
        if current_port and self.port_combo.findText(current_port) >= 0:
            self.port_combo.setCurrentText(current_port)

    def show_port_info(self):
        """显示选中端口的详细信息"""
        if not self.port_combo.currentText():
            QMessageBox.information(self, "提示", "请先选择一个端口")
            return

        port_name = self.port_combo.currentText().split(" - ")[0]
        ports = serial.tools.list_ports.comports()

        found = False
        for port in ports:
            if port.device == port_name:
                found = True
                info = f"设备: {port.device}\n"
                info += f"名称: {port.name}\n"
                info += f"描述: {port.description}\n"

                # 使用getattr安全访问可能不存在的属性
                manufacturer = getattr(port, 'manufacturer', None)
                if manufacturer:
                    info += f"厂商: {manufacturer}\n"

                product = getattr(port, 'product', None)
                if product:
                    info += f"产品ID: {product}\n"

                location = getattr(port, 'location', None)
                if location:
                    info += f"位置: {location}\n"

                # 尝试获取USB信息
                try:
                    usb_info = getattr(port, 'usb_info', lambda: None)()
                    if usb_info:
                        info += f"USB信息: {usb_info}\n"
                except:
                    pass

                # 尝试获取其他可能的属性
                try:
                    vid = getattr(port, 'vid', None)
                    pid = getattr(port, 'pid', None)
                    if vid and pid:
                        info += f"VID/PID: {vid:04X}:{pid:04X}\n"

                    serial_number = getattr(port, 'serial_number', None)
                    if serial_number:
                        info += f"序列号: {serial_number}\n"
                except:
                    pass

                QMessageBox.information(self, "端口信息", info)
                return

        if not found:
            QMessageBox.warning(self, "错误", f"未找到端口 {port_name} 的详细信息")


    def toggle_connection(self):
        """切换串口连接状态（打开/关闭）"""
        if self.serial_port and self.serial_port.is_open:
            # 关闭串口
            self.close_serial()
            self.connect_btn.setText("打开串口 📶")
            self.connect_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ColorTheme.SUCCESS};
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {ColorTheme.ACCENT};
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    border: none;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                }}
            """)
            self.send_btn.setEnabled(False)
            self.send_file_btn.setEnabled(False)
            self.port_info_btn.setEnabled(False)
            self.append_receive_data("串口已关闭\n", ColorTheme.WARNING)
        else:
            # 打开串口
            if self.open_serial():
                self.connect_btn.setText("关闭串口 🛑")
                self.connect_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {ColorTheme.ACCENT};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {ColorTheme.SUCCESS};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                    }}
                """)
                self.send_btn.setEnabled(True)
                self.send_file_btn.setEnabled(True)
                self.port_info_btn.setEnabled(True)
                self.append_receive_data("串口已打开\n", ColorTheme.SUCCESS)

    def open_serial(self):
        """打开串口"""
        try:
            # 获取选中的端口和参数
            port_text = self.port_combo.currentText()
            if not port_text:
                self.append_receive_data("请选择串口号\n", ColorTheme.WARNING)
                return False

            port_name = port_text.split(" - ")[0]
            baudrate = int(self.baudrate_combo.currentText())

            # 转换数据位
            databits = int(self.databits_combo.currentText())

            # 转换校验位
            parity_map = {
                "无": serial.PARITY_NONE,
                "奇校验": serial.PARITY_ODD,
                "偶校验": serial.PARITY_EVEN,
                "标记": serial.PARITY_MARK,
                "空格": serial.PARITY_SPACE
            }
            parity = parity_map[self.parity_combo.currentText()]

            # 转换停止位
            stopbits_map = {
                "1": serial.STOPBITS_ONE,
                "1.5": serial.STOPBITS_ONE_POINT_FIVE,
                "2": serial.STOPBITS_TWO
            }
            stopbits = stopbits_map[self.stopbits_combo.currentText()]

            # 转换流控制
            flowcontrol_map = {
                "无": 0,
                "硬件": 1,
                "软件": 2
            }
            flowcontrol = flowcontrol_map[self.flowcontrol_combo.currentText()]

            # 初始化串口
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                timeout=0.1,
                parity=parity,
                stopbits=stopbits,
                bytesize=databits,
                rtscts=(flowcontrol == 1),
                xonxoff=(flowcontrol == 2)
            )

            # 获取当前编码设置
            current_encoding = ENCODING_OPTIONS[self.receive_encoding_combo.currentText()]
            current_error_handling = ERROR_HANDLING_OPTIONS[self.error_handling_combo.currentText()]

            # 启动接收线程
            self.serial_thread = SerialThread(
                self.serial_port,
                self.hex_receive_check.isChecked(),
                current_encoding,
                current_error_handling
            )
            self.serial_thread.data_received.connect(lambda data: self.append_receive_data(data, ColorTheme.LIGHT))
            self.serial_thread.error_occurred.connect(lambda data: self.append_receive_data(data, ColorTheme.ACCENT))
            self.serial_thread.start()

            # 初始化接收计数
            self.receive_byte_count = 0

            return True

        except Exception as e:
            self.append_receive_data(f"打开串口失败: {str(e)}\n", ColorTheme.ACCENT)
            return False

    def close_serial(self):
        """关闭串口"""
        # 停止定时发送
        if self.timer.isActive():
            self.timer.stop()
            self.timed_send_check.setChecked(False)
            self.toggle_timed_send()

        # 停止文件发送线程
        if self.file_send_thread and self.file_send_thread.isRunning():
            self.file_send_thread.stop()
            self.file_send_thread = None

        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None

        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    def append_receive_data(self, data, color=ColorTheme.LIGHT):
        """添加接收的数据到显示区域，支持彩色显示"""
        # 获取当前文本的最后一个字符
        current_text = self.receive_text.toPlainText()

        # 如果当前文本不为空且最后一个字符不是换行符，则先添加一个换行符
        if current_text and current_text[-1] != '\n':
            self.receive_text.insertPlainText('\n')

        # 更新接收字节数统计
        if not self.hex_receive_check.isChecked() and self.serial_thread:
            encoding = ENCODING_OPTIONS[self.receive_encoding_combo.currentText()]
            try:
                # 估算字节数（实际可能有差异，精确统计需在接收线程中实现）
                self.receive_byte_count += len(data.encode(encoding))
                self.receive_count_label.setText(f"接收字节数: {self.receive_byte_count}")
            except:
                pass

        # 如果需要显示时间戳
        if self.timestamp_check.isChecked():
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
            self.receive_text.insertHtml(f'<span style="color:{ColorTheme.INFO}">[{timestamp}] </span>')

        # 设置文本颜色
        self.receive_text.insertHtml(f'<span style="color:{color}">{data}</span>')

        # 确保每条消息都以换行符结束
        if not data.endswith('\n'):
            self.receive_text.insertPlainText('\n')

        # 滚动到最底部
        self.receive_text.moveCursor(QTextCursor.End)

    def clear_receive_area(self):
        """清空接收区并重置计数"""
        self.receive_text.clear()
        self.receive_byte_count = 0
        self.receive_count_label.setText(f"接收字节数: {self.receive_byte_count}")
        self.last_search_pos = 0  # 重置搜索位置

    def toggle_hex_receive(self):
        """切换十六进制接收模式"""
        if self.serial_thread:
            self.serial_thread.update_settings(hex_mode=self.hex_receive_check.isChecked())

    def on_receive_encoding_changed(self):
        """接收编码格式变更时更新"""
        if self.serial_thread:
            new_encoding = ENCODING_OPTIONS[self.receive_encoding_combo.currentText()]
            self.serial_thread.update_settings(encoding=new_encoding)

    def on_error_handling_changed(self):
        """编码错误处理方式变更时更新"""
        if self.serial_thread:
            new_handling = ERROR_HANDLING_OPTIONS[self.error_handling_combo.currentText()]
            self.serial_thread.update_settings(error_handling=new_handling)

    def check_hex_input(self):
        """检查十六进制输入是否有效"""
        if not self.hex_send_check.isChecked():
            return

        text = self.send_text.text()
        # 简单验证十六进制格式
        allowed_chars = set('0123456789ABCDEFabcdef ')
        if not all(c in allowed_chars for c in text):
            QMessageBox.warning(self, "无效输入", "十六进制模式下只能输入0-9, A-F, a-f和空格")
            # 过滤无效字符
            filtered = ''.join([c for c in text if c in allowed_chars])
            self.send_text.setText(filtered)

    def send_data(self):
        """发送数据（支持多种编码格式）"""
        if not self.serial_port or not self.serial_port.is_open:
            return

        data = self.send_text.text()
        if not data:
            return

        # 保存到历史记录
        self.add_to_history(data)

        try:
            # 获取发送编码
            send_encoding = ENCODING_OPTIONS[self.send_encoding_combo.currentText()]

            # 如果是十六进制发送模式
            if self.hex_send_check.isChecked():
                # 移除所有空格
                data = data.replace(' ', '')
                # 转换为字节
                send_bytes = bytes.fromhex(data)
            else:
                # 普通文本模式（使用选择的编码）
                send_bytes = data.encode(send_encoding, errors='replace')
                # 如果需要添加换行
                if self.append_newline_check.isChecked():
                    send_bytes += b'\r\n'

            # 发送数据
            self.serial_port.write(send_bytes)

            # 显示发送的内容
            display_text = f"已发送: {data} (编码: {self.send_encoding_combo.currentText()})"
            if self.append_newline_check.isChecked() and not self.hex_send_check.isChecked():
                display_text += " (含换行)"
            self.append_receive_data(f"{display_text}\n", ColorTheme.SUCCESS)

            # 如果需要发送时清空接收区
            if self.clear_on_send_check.isChecked():
                self.clear_receive_area()

        except Exception as e:
            self.append_receive_data(f"发送失败: {str(e)}\n", ColorTheme.ACCENT)

    def save_received_data(self):
        """保存接收的数据到文件"""
        if not self.receive_text.toPlainText():
            QMessageBox.information(self, "提示", "接收区没有数据可保存")
            return

        # 获取保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存接收数据", f"serial_data_{time.strftime('%Y%m%d_%H%M%S')}.txt", "文本文件 (*.txt);;所有文件 (*)"
        )

        if not file_path:
            return

        # 保存文件
        file = QFile(file_path)
        if file.open(QIODevice.WriteOnly | QIODevice.Text):
            stream = QTextStream(file)
            stream << self.receive_text.toPlainText()
            file.close()
            QMessageBox.information(self, "成功", f"数据已保存到:\n{file_path}")
        else:
            QMessageBox.warning(self, "失败", f"无法保存文件:\n{file.errorString()}")

    # 定时发送功能
    def toggle_timed_send(self):
        """切换定时发送状态"""
        if self.timed_send_check.isChecked():
            self.interval_label.setEnabled(True)
            self.interval_spin.setEnabled(True)
            self.timer.start(self.interval_spin.value())
            self.append_receive_data(f"已启动定时发送，间隔 {self.interval_spin.value()} ms\n", ColorTheme.INFO)
        else:
            self.interval_label.setEnabled(False)
            self.interval_spin.setEnabled(False)
            self.timer.stop()
            self.append_receive_data("已停止定时发送\n", ColorTheme.INFO)

    # 文件发送功能
    def select_file(self):
        """选择要发送的文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择要发送的文件", "", "所有文件 (*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)

    def send_file(self):
        """发送文件"""
        if not self.serial_port or not self.serial_port.is_open:
            QMessageBox.warning(self, "错误", "请先打开串口")
            return

        file_path = self.file_path_edit.text()
        if not file_path or not QFile.exists(file_path):
            QMessageBox.warning(self, "错误", "请选择有效的文件")
            return

        # 创建进度对话框
        progress_dialog = QProgressDialog("正在发送文件...", "取消", 0, 100, self)
        progress_dialog.setWindowTitle("文件发送")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()

        # 停止定时发送（如果正在运行）
        was_timed_sending = False
        if self.timer.isActive():
            was_timed_sending = True
            self.timer.stop()

        # 创建并启动文件发送线程
        self.file_send_thread = FileSendThread(
            self.serial_port,
            file_path,
            self.hex_send_check.isChecked(),
            ENCODING_OPTIONS[self.send_encoding_combo.currentText()]
        )

        # 连接信号
        self.file_send_thread.progress_updated.connect(progress_dialog.setValue)
        self.file_send_thread.finished.connect(
            lambda success, msg: self.on_file_send_finished(success, msg, progress_dialog, was_timed_sending))
        progress_dialog.canceled.connect(self.file_send_thread.stop)

        self.file_send_thread.start()

    def on_file_send_finished(self, success, message, progress_dialog, was_timed_sending):
        """文件发送完成后的处理"""
        progress_dialog.close()
        color = ColorTheme.SUCCESS if success else ColorTheme.ACCENT
        self.append_receive_data(f"{message}\n", color)
        self.file_send_thread = None

        # 如果之前在定时发送，恢复定时发送
        if was_timed_sending and self.timed_send_check.isChecked():
            self.timer.start(self.interval_spin.value())

    # 文本搜索功能
    def search_text(self):
        """在接收区搜索文本"""
        search_text = self.search_input.text()
        if not search_text:
            return

        # 获取文本内容
        text = self.receive_text.toPlainText()
        # 获取当前光标
        cursor = self.receive_text.textCursor()

        # 设置搜索选项
        flags = Qt.CaseSensitive if self.search_case_sensitive.isChecked() else Qt.CaseInsensitive

        # 从上次搜索位置开始搜索
        pos = self.last_search_pos
        # 使用 Python 字符串的 find 方法而不是 indexOf
        if flags == Qt.CaseSensitive:
            index = text.find(search_text, pos)
        else:
            # 不区分大小写，将文本和搜索文本都转换为小写再查找
            index = text.lower().find(search_text.lower(), pos)

        # 如果没找到，从头开始搜索
        if index == -1:
            if flags == Qt.CaseSensitive:
                index = text.find(search_text, 0)
            else:
                index = text.lower().find(search_text.lower(), 0)
            if index == -1:
                QMessageBox.information(self, "搜索", f"找不到 '{search_text}'")
                return
            else:
                QMessageBox.information(self, "搜索", f"已到达末尾，从头开始搜索 '{search_text}'")

        # 更新搜索位置
        self.last_search_pos = index + len(search_text)

        # 高亮显示搜索结果
        cursor.setPosition(index)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(search_text))
        self.receive_text.setTextCursor(cursor)

        # 确保可见
        self.receive_text.ensureCursorVisible()

    # 发送预设功能
    def add_to_preset(self):
        """添加当前发送框内容到预设"""
        text = self.send_text.text()
        if not text:
            QMessageBox.warning(self, "警告", "发送框内容为空，无法添加到预设")
            return

        # 检查是否已存在
        for i in range(self.preset_list.count()):
            if self.preset_list.item(i).text() == text:
                QMessageBox.information(self, "提示", "该内容已在预设列表中")
                return

        self.send_presets.append(text)
        self.preset_list.addItem(text)
        self.append_receive_data("已添加到发送预设\n", ColorTheme.INFO)

    def use_preset(self, item):
        """使用选中的预设"""
        self.send_text.setText(item.text())
        # 切换到即时发送标签
        self.sender().parent().setCurrentIndex(0)

    def show_preset_context_menu(self, position):
        """显示预设的右键菜单"""
        if not self.preset_list.itemAt(position):
            return

        menu = QMenu()
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_preset())

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self.edit_preset())

        menu.addAction(delete_action)
        menu.addAction(edit_action)
        menu.exec_(self.preset_list.mapToGlobal(position))

    def delete_preset(self):
        """删除选中的预设"""
        current_item = self.preset_list.currentItem()
        if current_item:
            text = current_item.text()
            if text in self.send_presets:
                self.send_presets.remove(text)
            self.preset_list.takeItem(self.preset_list.row(current_item))

    def edit_preset(self):
        """编辑选中的预设"""
        current_item = self.preset_list.currentItem()
        if current_item:
            old_text = current_item.text()
            new_text, ok = QInputDialog.getText(self, "编辑预设", "修改预设内容:", text=old_text)
            if ok and new_text != old_text:
                index = self.send_presets.index(old_text)
                self.send_presets[index] = new_text
                current_item.setText(new_text)

    def save_presets(self):
        """保存预设到文件"""
        if not self.send_presets:
            QMessageBox.information(self, "提示", "没有预设可保存")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存预设", "presets.txt", "文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for preset in self.send_presets:
                        f.write(preset + '\n')
                QMessageBox.information(self, "成功", f"预设已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"保存预设失败:\n{str(e)}")

    def load_presets_dialog(self):
        """从文件加载预设"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载预设", "", "文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            self.load_presets(file_path)

    def load_presets(self, file_path=None):
        """加载预设（默认从本地配置加载）"""
        self.send_presets.clear()
        self.preset_list.clear()

        if not file_path:
            # 尝试从默认位置加载
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.rstrip('\n')
                    if line:  # 跳过空行
                        self.send_presets.append(line)
                        self.preset_list.addItem(line)
            QMessageBox.information(self, "成功", f"已从文件加载 {len(self.send_presets)} 个预设")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"加载预设失败:\n{str(e)}")

    def clear_presets(self):
        """清空所有预设"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有预设吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.send_presets.clear()
            self.preset_list.clear()

    def closeEvent(self, event):
        """窗口关闭时确保资源释放"""
        self.close_serial()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置中文字体支持
    font = app.font()
    font.setFamily("SimHei")
    app.setFont(font)

    window = SerialMonitor()
    window.show()
    sys.exit(app.exec())