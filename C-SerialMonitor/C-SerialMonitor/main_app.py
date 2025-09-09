import sys
import serial
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QTextEdit, QLineEdit, QGroupBox, QFormLayout, 
    QCheckBox, QSplitter, QMessageBox, QListWidget, QListWidgetItem, 
    QFileDialog, QSpinBox, QTabWidget, QProgressDialog, QMenu, QInputDialog
)
from PySide6.QtCore import (
    QThread, Signal, Qt, QDateTime, QEvent, QFile, 
    QIODevice, QTimer, QTextStream
)
from PySide6.QtGui import (
    QFont, QTextCursor, QColor, QTextCharFormat, 
    QContextMenuEvent, QAction, QPalette, QLinearGradient, 
    QBrush, QIcon, QPainter, QPen, QShortcut, QKeySequence
)

# 导入自定义模块
from theme_manager import ThemeManager, THEMES
from serial_threads import SerialThread, FileSendThread
from custom_widgets import GradientGroupBox, HoverButton
from serial_config import SerialConfig
from preset_manager import PresetManager
from connection_manager import ConnectionManager, DataReceiveThread, ConnectionError


class SerialMonitor(QMainWindow):
    """支持多编码格式的增强版串口监控主窗口"""

    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.serial_thread = None
        self.file_send_thread = None
        self.send_history = []  # 发送历史记录
        self.history_index = -1  # 历史记录索引，用于上下键切换
        self.timer = QTimer(self)  # 定时发送计时器
        self.timer.timeout.connect(self.send_data)
        self.preset_manager = PresetManager()
        
        # 添加连接管理器
        self.connection_manager = ConnectionManager()
        
        # 添加数据历史记录，用于格式转换
        self.data_history = []  # 存储原始数据的历史记录
        self.last_search_pos = 0  # 搜索位置

        # 设置窗口标题和大小 - 适配笔记本电脑屏幕，约占屏幕一半大小
        self.setWindowTitle("串口调试工具 🚀")
        self.setGeometry(100, 100, 800, 1000)  # 调整窗口大小为800x600
        
        # 设置最小窗口大小，防止用户调整到太小
        self.setMinimumSize(700, 500)

        # 创建所有按钮的引用列表，用于主题切换时更新样式
        self.buttons = []

        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建主题选择区域
        self.create_theme_selector(main_layout)

        # 创建连接类型选择区域
        self.create_connection_type_selector(main_layout)
        
        # 创建连接配置区域
        self.create_config_group(main_layout)

        # 创建数据显示和发送区域的分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet(ThemeManager.get_splitter_style())
        self.splitter = splitter

        # 创建接收区域
        self.create_receive_group(splitter)

        # 创建发送区域和预设区域的Tab
        send_tab_widget = QTabWidget()
        send_tab_widget.setStyleSheet("""
            QTabWidget::tab-bar {
                alignment: center;
            }
        """)
        # 设置TabWidget的最小高度，防止内容被压缩，但适应小窗口
        send_tab_widget.setMinimumHeight(150)
        self.send_tab_widget = send_tab_widget
        self.create_send_group(send_tab_widget)
        self.create_preset_group(send_tab_widget)
        splitter.addWidget(send_tab_widget)

        # 设置分割器初始大小和拉伸因子 - 调整比例给下方发送区域更多空间
        splitter.setSizes([300, 250])  # 调整比例为300:250
        main_layout.addWidget(splitter, 1)  # 添加拉伸因子，使分割器占满空间

        # 初始化串口列表
        self.refresh_serial_ports()
        # 加载发送预设
        self.load_presets()

        # 应用初始样式
        self.apply_stylesheet()

        # 窗口大小变化时重新布局
        self.resizeEvent = self.on_resize

        # 禁用发送按钮和RTS/DTR控制
        self.send_btn.setEnabled(False)
        self.send_btn.setStyleSheet(self.send_btn.disabled_style)
        self.rts_check.setEnabled(False)
        self.dtr_check.setEnabled(False)
        
        # 初始时隐藏网络连接参数
        self.tcp_param_group.hide()
        self.udp_param_group.hide()
        self.bluetooth_param_group.hide()

    def create_theme_selector(self, parent_layout):
        """创建主题选择器"""
        theme_layout = QHBoxLayout()
        theme_label = QLabel("主题颜色:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(ThemeManager.get_all_themes())
        self.theme_combo.setCurrentText("蓝色")  # 默认蓝色主题
        self.theme_combo.currentIndexChanged.connect(self.change_theme)

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()

        parent_layout.addLayout(theme_layout)
        
    def create_connection_type_selector(self, parent_layout):
        """创建连接类型选择器"""
        conn_type_layout = QHBoxLayout()
        conn_type_label = QLabel("连接类型:")
        self.connection_type_combo = QComboBox()
        self.connection_type_combo.addItems(["串口", "TCP服务器", "TCP客户端", "UDP", "WiFi服务器", "WiFi客户端", "以太网服务器", "以太网客户端", "蓝牙"])
        self.connection_type_combo.currentIndexChanged.connect(self.on_connection_type_changed)
        
        conn_type_layout.addWidget(conn_type_label)
        conn_type_layout.addWidget(self.connection_type_combo)
        conn_type_layout.addStretch()
        
        parent_layout.addLayout(conn_type_layout)

    def on_connection_type_changed(self, index):
        """连接类型改变时的处理"""
        # 隐藏所有参数组
        self.serial_param_group.hide()
        self.tcp_param_group.hide()
        self.udp_param_group.hide()
        self.bluetooth_param_group.hide()
        
        # 根据选择显示相应的参数组
        conn_type = self.connection_type_combo.currentText()
        if conn_type.startswith("串口"):
            self.serial_param_group.show()
            self.refresh_serial_ports()
        elif conn_type.startswith("TCP") or conn_type.startswith("WiFi") or conn_type.startswith("以太网"):
            self.tcp_param_group.show()
        elif conn_type.startswith("UDP"):
            self.udp_param_group.show()
        elif conn_type.startswith("蓝牙"):
            self.bluetooth_param_group.show()

    def change_theme(self):
        """切换主题颜色"""
        theme_name = self.theme_combo.currentText()
        ThemeManager.set_theme(theme_name)
        current_theme = ThemeManager.get_theme()

        # 更新所有样式
        self.apply_stylesheet()

        # 更新所有按钮样式
        for button in self.buttons:
            if isinstance(button, HoverButton):
                button.update_style()
            else:
                # 更新普通按钮样式
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {current_theme["SECONDARY"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {current_theme["ACCENT"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                """)

        # 更新GroupBox样式
        if hasattr(self, 'serial_param_group'):
            self.serial_param_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)

        if hasattr(self, 'tcp_param_group'):
            self.tcp_param_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)

        if hasattr(self, 'udp_param_group'):
            self.udp_param_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)

        if hasattr(self, 'bluetooth_param_group'):
            self.bluetooth_param_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)

        if hasattr(self, 'receive_group'):
            self.receive_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)

        if hasattr(self, 'send_group'):
            self.send_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)

        if hasattr(self, 'preset_group'):
            self.preset_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)


        # 特殊按钮样式更新
        if hasattr(self, 'connect_btn'):
            if self.connection_manager.current_connection and self.connection_manager.current_connection.is_connected:
                self.connect_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {current_theme["ACCENT"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {current_theme["SUCCESS"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                """)
            else:
                self.connect_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {current_theme["SUCCESS"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {current_theme["ACCENT"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                """)

        if hasattr(self, 'send_btn'):
            # 更新发送按钮样式
            self.send_btn.normal_style = f"""
                    QPushButton {{
                        background-color: {current_theme["SUCCESS"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                """
            self.send_btn.hover_style = f"""
                    QPushButton {{
                        background-color: {current_theme["ACCENT"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                """
            self.send_btn.disabled_style = f"""
                    QPushButton {{
                        background-color: #CCCCCC;
                        color: #666666;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                """
            if self.send_btn.isEnabled():
                self.send_btn.setStyleSheet(self.send_btn.normal_style)
            else:
                self.send_btn.setStyleSheet(self.send_btn.disabled_style)

        # 刷新界面
        self.update()

    def apply_stylesheet(self):
        """应用样式表"""
        current_theme = ThemeManager.get_theme()
        self.setStyleSheet(ThemeManager.get_style_sheet())

        # 更新分割器样式
        if hasattr(self, 'splitter'):
            self.splitter.setStyleSheet(ThemeManager.get_splitter_style())

        # 更新TabWidget样式
        if hasattr(self, 'send_tab_widget'):
            self.send_tab_widget.setStyleSheet(f"""
                QTabWidget::tab-bar {{
                    alignment: center;
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
            """)

        # 更新接收文本区域样式
        if hasattr(self, 'receive_text'):
            self.receive_text.setStyleSheet(ThemeManager.get_receive_text_style())

        # 更新发送文本区域样式（QTextEdit）
        if hasattr(self, 'send_text'):
            self.send_text.setStyleSheet(ThemeManager.get_send_text_style())
            
        # 更新GroupBox样式
        if hasattr(self, 'serial_param_group'):
            self.serial_param_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)
            
        if hasattr(self, 'tcp_param_group'):
            self.tcp_param_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)
            
        if hasattr(self, 'udp_param_group'):
            self.udp_param_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)
            
        if hasattr(self, 'bluetooth_param_group'):
            self.bluetooth_param_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)
            
        if hasattr(self, 'receive_group'):
            self.receive_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)
            
        if hasattr(self, 'send_group'):
            self.send_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)
            
        if hasattr(self, 'preset_group'):
            self.preset_group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {current_theme["GROUP_BOX"]};
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
            """)
            
        # 更新所有按钮样式
        for button in self.buttons:
            if not isinstance(button, HoverButton):
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {current_theme["SECONDARY"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {current_theme["ACCENT"]};
                        color: white;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                        border: none;
                    }}
                """)


        # 更新历史列表样式
        if hasattr(self, 'history_list'):
            self.history_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: {current_theme["PRIMARY"]};
                    color: {current_theme["DARK"]};
                    border: 1px solid {current_theme["SECONDARY"]};
                    border-radius: 6px;
                }}
                QListWidget::item:selected {{
                    background-color: {current_theme["SECONDARY"]};
                    color: white;
                }}
            """)

        # 更新预设列表样式
        if hasattr(self, 'preset_list'):
            self.preset_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: {current_theme["PRIMARY"]};
                    color: {current_theme["DARK"]};
                    border: 1px solid {current_theme["INFO"]};
                    border-radius: 6px;
                }}
                QListWidget::item:selected {{
                    background-color: {current_theme["INFO"]};
                    color: white;
                }}
            """)

    def on_resize(self, event):
        """窗口大小变化时的处理"""
        # 可以在这里添加自定义的布局调整逻辑
        super().resizeEvent(event)

    def create_config_group(self, parent_layout):
        """创建更丰富的连接配置区域，支持多种连接类型"""
        config_group = GradientGroupBox("连接配置 ⚙️")
        config_layout = QHBoxLayout()
        config_layout.setContentsMargins(10, 10, 10, 10)
        config_layout.setSpacing(15)

        # 创建串口参数组
        self.serial_param_group = QGroupBox("串口参数")
        serial_layout = QVBoxLayout()
        serial_sub_layout = QHBoxLayout()
        
        # 左侧布局
        left_layout = QFormLayout()
        left_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        left_layout.setSpacing(10)

        # 串口选择
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(200)
        left_layout.addRow("串口号:", self.port_combo)

        # 波特率选择
        self.baudrate_combo = QComboBox()
        baudrates = SerialConfig.get_default_baudrates()
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

        # 添加到串口参数布局
        serial_sub_layout.addLayout(left_layout, 2)
        serial_sub_layout.addLayout(right_layout, 2)
        serial_layout.addLayout(serial_sub_layout)
        self.serial_param_group.setLayout(serial_layout)

        # 创建TCP参数组
        self.tcp_param_group = QGroupBox("TCP参数")
        tcp_layout = QFormLayout()
        tcp_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        tcp_layout.setSpacing(10)

        # 主机地址
        self.tcp_host_edit = QLineEdit()
        self.tcp_host_edit.setPlaceholderText("例如: 127.0.0.1 或 localhost")
        tcp_layout.addRow("主机地址:", self.tcp_host_edit)

        # 端口号
        self.tcp_port_spin = QSpinBox()
        self.tcp_port_spin.setRange(1, 65535)
        self.tcp_port_spin.setValue(8080)
        tcp_layout.addRow("端口号:", self.tcp_port_spin)

        # 服务器/客户端模式
        self.tcp_mode_combo = QComboBox()
        self.tcp_mode_combo.addItems(["客户端", "服务器"])
        tcp_layout.addRow("模式:", self.tcp_mode_combo)
        self.tcp_param_group.setLayout(tcp_layout)

        # 创建UDP参数组
        self.udp_param_group = QGroupBox("UDP参数")
        udp_layout = QFormLayout()
        udp_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        udp_layout.setSpacing(10)

        # 本地地址
        self.udp_local_host_edit = QLineEdit()
        self.udp_local_host_edit.setPlaceholderText("例如: 0.0.0.0")
        self.udp_local_host_edit.setText("0.0.0.0")
        udp_layout.addRow("本地地址:", self.udp_local_host_edit)

        # 本地端口
        self.udp_local_port_spin = QSpinBox()
        self.udp_local_port_spin.setRange(1, 65535)
        self.udp_local_port_spin.setValue(8080)
        udp_layout.addRow("本地端口:", self.udp_local_port_spin)

        # 远程地址（可选）
        self.udp_remote_host_edit = QLineEdit()
        self.udp_remote_host_edit.setPlaceholderText("例如: 127.0.0.1 (可选)")
        udp_layout.addRow("远程地址:", self.udp_remote_host_edit)

        # 远程端口（可选）
        self.udp_remote_port_spin = QSpinBox()
        self.udp_remote_port_spin.setRange(1, 65535)
        self.udp_remote_port_spin.setValue(8080)
        udp_layout.addRow("远程端口:", self.udp_remote_port_spin)
        self.udp_param_group.setLayout(udp_layout)

        # 创建蓝牙参数组
        self.bluetooth_param_group = QGroupBox("蓝牙参数")
        bluetooth_layout = QVBoxLayout()
        bluetooth_sub_layout = QFormLayout()
        bluetooth_sub_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        bluetooth_sub_layout.setSpacing(10)

        # 蓝牙地址
        self.bluetooth_address_edit = QLineEdit()
        self.bluetooth_address_edit.setPlaceholderText("例如: 00:11:22:33:44:55")
        bluetooth_sub_layout.addRow("设备地址:", self.bluetooth_address_edit)

        # 蓝牙端口
        self.bluetooth_port_spin = QSpinBox()
        self.bluetooth_port_spin.setRange(1, 30)
        self.bluetooth_port_spin.setValue(1)
        bluetooth_sub_layout.addRow("端口:", self.bluetooth_port_spin)

        # 扫描蓝牙设备按钮
        self.scan_bluetooth_btn = QPushButton("扫描设备 🔍")
        self.scan_bluetooth_btn.clicked.connect(self.scan_bluetooth_devices)
        self.buttons.append(self.scan_bluetooth_btn)
        
        # 添加到蓝牙参数布局
        bluetooth_layout.addLayout(bluetooth_sub_layout)
        bluetooth_layout.addWidget(self.scan_bluetooth_btn)
        self.bluetooth_param_group.setLayout(bluetooth_layout)

        # 控制按钮布局
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)

        self.refresh_btn = HoverButton("刷新端口 🔄")
        self.refresh_btn.clicked.connect(self.refresh_serial_ports)
        self.buttons.append(self.refresh_btn)

        # 设置连接按钮
        self.connect_btn = HoverButton("打开连接 📶")
        current_theme = ThemeManager.get_theme()
        self.connect_btn.normal_style = f"""
            QPushButton {{
                background-color: {current_theme["SUCCESS"]};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
        """
        self.connect_btn.hover_style = f"""
            QPushButton {{
                background-color: {current_theme["ACCENT"]};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                border: none;
            }}
        """
        self.connect_btn.setStyleSheet(self.connect_btn.normal_style)
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.buttons.append(self.connect_btn)

        # 添加RTS和DTR控制
        self.rts_check = QCheckBox("RTS")
        self.rts_check.setToolTip("Request To Send")
        self.rts_check.setEnabled(False)  # 初始禁用
        self.rts_check.stateChanged.connect(lambda: self.set_rts())  # 忽略参数，直接调用

        self.dtr_check = QCheckBox("DTR")
        self.dtr_check.setToolTip("Data Terminal Ready")
        self.dtr_check.setEnabled(False)  # 初始禁用
        self.dtr_check.stateChanged.connect(lambda: self.set_dtr())  # 忽略参数，直接调用

        # 设置RTS/DTR复选框样式
        self.rts_check.setStyleSheet(f"color: {current_theme['DARK']};")
        self.dtr_check.setStyleSheet(f"color: {current_theme['DARK']};")

        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.connect_btn)
        button_layout.addSpacing(20)
        button_layout.addWidget(self.rts_check)
        button_layout.addWidget(self.dtr_check)
        button_layout.addStretch()

        # 添加到配置布局
        config_layout.addWidget(self.serial_param_group, 2)
        config_layout.addWidget(self.tcp_param_group, 2)
        config_layout.addWidget(self.udp_param_group, 2)
        config_layout.addWidget(self.bluetooth_param_group, 2)
        config_layout.addLayout(button_layout, 1)

        config_group.setLayout(config_layout)
        parent_layout.addWidget(config_group)
        
        # 初始化时只显示串口参数组
        self.tcp_param_group.hide()
        self.udp_param_group.hide()
        self.bluetooth_param_group.hide()

    def toggle_connection(self):
        """切换连接状态，支持多种连接类型"""
        # 检查当前是否有活动连接
        current_conn = self.connection_manager.get_current_connection()
        is_connected = current_conn and current_conn.is_connected
        current_theme = ThemeManager.get_theme()
        
        if is_connected:
            # 关闭当前连接
            self.close_serial()  # 使用现有的关闭方法
            
            # 更新按钮样式为正常状态
            self.connect_btn.setText("打开连接 📶")
            self.connect_btn.normal_style = f"""
                QPushButton {{            
                    background-color: {current_theme["SUCCESS"]};
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    border: none;
                }}
            """
            self.connect_btn.hover_style = f"""
                QPushButton {{            
                    background-color: {current_theme["ACCENT"]};
                    color: white;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    border: none;
                }}
            """
            self.connect_btn.setStyleSheet(self.connect_btn.normal_style)
            
            # 禁用发送按钮和RTS/DTR控制
            if hasattr(self, 'send_btn'):
                self.send_btn.setEnabled(False)
                self.send_btn.setStyleSheet(self.send_btn.disabled_style)
            
            self.rts_check.setEnabled(False)
            self.dtr_check.setEnabled(False)
        else:
            # 打开新连接
            try:
                connection_type = self.connection_type_combo.currentText()
                
                if connection_type.startswith("串口"):
                    # 获取串口参数
                    port_text = self.port_combo.currentText()
                    if not port_text:
                        QMessageBox.warning(self, "警告", "请选择串口")
                        return
                    
                    # 提取纯端口号 (例如从 "COM3 - USB Serial Port" 提取 "COM3")
                    port_name = port_text.split(" - ")[0] if " - " in port_text else port_text
                    
                    baudrate = int(self.baudrate_combo.currentText())
                    databits = int(self.databits_combo.currentText())
                    
                    # 转换校验位
                    parity_map = {"无": serial.PARITY_NONE, "奇校验": serial.PARITY_ODD, 
                                 "偶校验": serial.PARITY_EVEN, "标记": serial.PARITY_MARK, 
                                 "空格": serial.PARITY_SPACE}
                    parity = parity_map[self.parity_combo.currentText()]
                    
                    # 转换停止位
                    stopbits_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}
                    stopbits = stopbits_map[self.stopbits_combo.currentText()]
                    
                    # 创建串口连接
                    self.connection_manager.create_connection(
                        "serial", 
                        port_name=port_name, 
                        baudrate=baudrate, 
                        databits=databits, 
                        parity=parity, 
                        stopbits=stopbits
                    )
                elif connection_type.startswith("TCP") or connection_type.startswith("WiFi") or connection_type.startswith("以太网"):
                    # 获取TCP参数
                    host = self.tcp_host_edit.text()
                    port = self.tcp_port_spin.value()
                    is_server = self.tcp_mode_combo.currentText() == "服务器"
                    
                    # 根据连接类型确定连接名称
                    conn_type_name = "tcp"
                    if connection_type.startswith("WiFi"):
                        conn_type_name = "wifi"
                    elif connection_type.startswith("以太网"):
                        conn_type_name = "ethernet"
                    
                    # 创建连接
                    self.connection_manager.create_connection(
                        conn_type_name, 
                        host=host, 
                        port=port, 
                        is_server=is_server
                    )
                elif connection_type.startswith("UDP"):
                    # 获取UDP参数
                    local_host = self.udp_local_host_edit.text()
                    local_port = self.udp_local_port_spin.value()
                    remote_host = self.udp_remote_host_edit.text() if self.udp_remote_host_edit.text() else None
                    remote_port = self.udp_remote_port_spin.value() if remote_host else None
                    
                    # 创建UDP连接
                    self.connection_manager.create_connection(
                        "udp", 
                        local_host=local_host, 
                        local_port=local_port, 
                        remote_host=remote_host, 
                        remote_port=remote_port
                    )
                elif connection_type.startswith("蓝牙"):
                    # 获取蓝牙参数
                    address = self.bluetooth_address_edit.text()
                    port = self.bluetooth_port_spin.value()
                    
                    # 创建蓝牙连接
                    self.connection_manager.create_connection(
                        "bluetooth", 
                        address=address, 
                        port=port
                    )
                else:
                    QMessageBox.warning(self, "连接错误", f"不支持的连接类型: {connection_type}")
                    return
                
                # 尝试建立连接
                if self.connection_manager.connect():
                    # 连接成功
                    self.connect_btn.setText("关闭连接 📴")
                    # 更新按钮样式为连接状态
                    self.connect_btn.normal_style = f"""
                        QPushButton {{            
                            background-color: {current_theme["ACCENT"]};
                            color: white;
                            border-radius: 6px;
                            padding: 6px 12px;
                            font-weight: bold;
                            border: none;
                        }}
                    """
                    self.connect_btn.hover_style = f"""
                        QPushButton {{            
                            background-color: {current_theme["SUCCESS"]};
                            color: white;
                            border-radius: 6px;
                            padding: 6px 12px;
                            font-weight: bold;
                            border: none;
                        }}
                    """
                    self.connect_btn.setStyleSheet(self.connect_btn.normal_style)
                    
                    # 启用发送按钮
                    if hasattr(self, 'send_btn'):
                        self.send_btn.setEnabled(True)
                        self.send_btn.setStyleSheet(self.send_btn.normal_style)
                    
                    # 只对串口连接启用RTS/DTR控制
                    self.rts_check.setEnabled(connection_type.startswith("串口"))
                    self.dtr_check.setEnabled(connection_type.startswith("串口"))
                    
                    # 更新状态信息
                    conn_info = self.connection_manager.get_connection_info()
                    self.statusBar().showMessage(f"已连接: {conn_info}")
                    
                    # 启动接收线程
                    self.serial_thread = DataReceiveThread(
                        self.connection_manager.get_current_connection(),
                        hex_mode=self.hex_receive_check.isChecked(),
                        encoding=SerialConfig.get_encoding_value(self.receive_encoding_combo.currentText()),
                        error_handling=SerialConfig.get_error_handling_value(self.error_handling_combo.currentText())
                    )
                    # 连接原始数据信号到新的处理方法
                    self.serial_thread.raw_data_received.connect(self.append_raw_received_data)
                    self.serial_thread.error_occurred.connect(lambda error: QMessageBox.critical(self, "接收错误", error))
                    self.serial_thread.start()
                    
                else:
                    # 连接失败
                    QMessageBox.warning(self, "连接失败", "无法建立连接，请检查参数设置。")
                    
            except ConnectionError as e:
                QMessageBox.critical(self, "连接错误", str(e))
            except Exception as e:
                QMessageBox.critical(self, "错误", f"发生未知错误: {str(e)}")

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
        self.receive_encoding_combo.addItems(SerialConfig.get_encoding_options())
        self.receive_encoding_combo.setCurrentText("UTF-8")
        self.receive_encoding_combo.currentIndexChanged.connect(self.on_receive_encoding_changed)

        error_handling_label = QLabel("错误处理:")
        self.error_handling_combo = QComboBox()
        self.error_handling_combo.addItems(SerialConfig.get_error_handling_options())
        self.error_handling_combo.setCurrentText("替换错误 (�)")
        self.error_handling_combo.currentIndexChanged.connect(self.on_error_handling_changed)

        # 搜索功能
        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索内容...")
        self.search_btn = HoverButton("查找下一个 🔍")
        self.search_btn.clicked.connect(self.search_text)
        self.buttons.append(self.search_btn)
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
        self.receive_text.setStyleSheet(ThemeManager.get_receive_text_style())
        self.last_search_pos = 0  # 上次搜索位置

        # 统计信息
        stats_layout = QHBoxLayout()
        current_theme = ThemeManager.get_theme()
        self.receive_count_label = QLabel("接收字节数: 0")
        self.receive_count_label.setStyleSheet(f"color: {current_theme['INFO']}; font-weight: bold;")
        stats_layout.addWidget(self.receive_count_label)
        stats_layout.addStretch()

        # 接收区按钮
        btn_layout = QHBoxLayout()
        self.clear_receive_btn = HoverButton("清空接收区 🗑️")
        self.clear_receive_btn.clicked.connect(self.clear_receive_area)
        self.buttons.append(self.clear_receive_btn)

        self.save_receive_btn = HoverButton("保存接收数据 💾")
        self.save_receive_btn.clicked.connect(self.save_received_data)
        self.buttons.append(self.save_receive_btn)

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
        """创建数据发送区域（增加定时发送功能）"""
        send_group = GradientGroupBox("发送数据 📤")
        send_layout = QVBoxLayout()
        send_layout.setContentsMargins(10, 10, 10, 10)
        send_layout.setSpacing(12)  # 增加布局间距

        # 发送选项
        options_layout = QHBoxLayout()

        # 添加"发送后清空"勾选框
        self.clear_after_send_check = QCheckBox("发送后清空 🗑️")
        self.clear_after_send_check.setChecked(True)  # 默认勾选

        # 新增定时发送相关控件
        self.timed_send_check = QCheckBox("定时发送 ⏳")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 30000)  # 100ms到30秒
        self.interval_spin.setValue(1000)  # 默认1秒
        self.interval_spin.setSuffix(" ms")
        self.interval_spin.setEnabled(False)  # 初始禁用

        # 关联定时发送复选框状态变化
        self.timed_send_check.stateChanged.connect(self.toggle_timed_send)

        self.hex_send_check = QCheckBox("十六进制发送 🧮")
        self.append_newline_check = QCheckBox("自动添加换行符 ↩️")

        options_layout.addWidget(self.hex_send_check)
        options_layout.addWidget(self.append_newline_check)
        options_layout.addWidget(self.clear_after_send_check)
        options_layout.addSpacing(20)
        options_layout.addWidget(self.timed_send_check)
        options_layout.addWidget(self.interval_spin)
        options_layout.addStretch()

        # 发送编码选择
        encoding_layout = QHBoxLayout()
        encoding_label = QLabel("发送编码:")
        self.send_encoding_combo = QComboBox()
        self.send_encoding_combo.addItems(SerialConfig.get_encoding_options())
        self.send_encoding_combo.setCurrentText("UTF-8")

        encoding_layout.addWidget(encoding_label)
        encoding_layout.addWidget(self.send_encoding_combo)
        encoding_layout.addStretch()

        # 发送区域和按钮（支持多行输入）
        send_input_layout = QHBoxLayout()
        # 使用QTextEdit（支持多行）
        self.send_text = QTextEdit()
        self.send_text.setPlaceholderText("输入要发送的数据...（Enter换行，Ctrl+Enter发送）")
        self.send_text.setFixedHeight(60)  # 减小高度以适应小窗口
        self.send_text.setLineWrapMode(QTextEdit.WidgetWidth)  # 自动换行
        self.send_text.setTabChangesFocus(True)  # Tab键切换焦点（避免输入Tab符）

        # 添加快捷键：Ctrl+Enter触发发送
        send_shortcut = QShortcut(QKeySequence("Ctrl+Enter"), self.send_text)
        send_shortcut.activated.connect(self.send_data)

        self.send_btn = HoverButton("发送数据 🚀")
        self.send_btn.clicked.connect(self.send_data)
        self.buttons.append(self.send_btn)

        # 历史记录按钮
        self.history_btn = HoverButton("历史记录 ⏱️")
        self.history_btn.clicked.connect(self.show_history)
        self.buttons.append(self.history_btn)

        # 保持布局比例（文本框占5份，按钮各占1份）
        send_input_layout.addWidget(self.send_text, 5)
        send_input_layout.addWidget(self.send_btn, 1)
        send_input_layout.addWidget(self.history_btn, 1)

        # 文件发送功能 - 改为两行布局，避免在小窗口下重叠
        file_layout = QVBoxLayout()
        file_layout.setSpacing(8)  # 减小行间距
        
        # 第一行：文件路径输入框
        file_path_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择要发送的文件...")
        file_path_layout.addWidget(self.file_path_edit)
        
        # 第二行：按钮组
        file_btn_layout = QHBoxLayout()
        self.browse_btn = HoverButton("浏览文件 📂")
        self.browse_btn.clicked.connect(self.browse_file)
        self.buttons.append(self.browse_btn)
        self.send_file_btn = HoverButton("发送文件 📤")
        self.send_file_btn.clicked.connect(self.send_file)
        self.buttons.append(self.send_file_btn)
        
        file_btn_layout.addWidget(self.browse_btn)
        file_btn_layout.addWidget(self.send_file_btn)
        
        # 添加到文件布局
        file_layout.addLayout(file_path_layout)
        file_layout.addLayout(file_btn_layout)

        # 添加到发送布局
        send_layout.addLayout(options_layout)
        send_layout.addLayout(encoding_layout)
        send_layout.addLayout(send_input_layout)
        send_layout.addSpacing(5)  # 减小间距以适应更紧凑的布局
        send_layout.addLayout(file_layout)

        send_group.setLayout(send_layout)
        parent.addTab(send_group, "即时发送")

    def create_preset_group(self, parent):
        """创建发送预设区域"""
        preset_widget = QWidget()
        preset_layout = QVBoxLayout(preset_widget)
        preset_layout.setContentsMargins(10, 10, 10, 10)
        preset_layout.setSpacing(10)

        # 预设操作按钮
        preset_btn_layout = QHBoxLayout()
        preset_btn_layout.setSpacing(10)

        self.add_preset_btn = HoverButton("添加预设 ➕")
        self.add_preset_btn.clicked.connect(self.add_preset)
        self.buttons.append(self.add_preset_btn)

        self.edit_preset_btn = HoverButton("编辑预设 ✏️")
        self.edit_preset_btn.clicked.connect(self.edit_preset)
        self.buttons.append(self.edit_preset_btn)

        self.delete_preset_btn = HoverButton("删除预设 🗑️")
        self.delete_preset_btn.clicked.connect(self.delete_preset)
        self.buttons.append(self.delete_preset_btn)

        self.load_preset_btn = HoverButton("加载预设 📂")
        self.load_preset_btn.clicked.connect(self.load_presets_from_file)
        self.buttons.append(self.load_preset_btn)

        self.save_preset_btn = HoverButton("保存预设 💾")
        self.save_preset_btn.clicked.connect(self.save_presets_to_file)
        self.buttons.append(self.save_preset_btn)

        preset_btn_layout.addWidget(self.add_preset_btn)
        preset_btn_layout.addWidget(self.edit_preset_btn)
        preset_btn_layout.addWidget(self.delete_preset_btn)
        preset_btn_layout.addWidget(self.load_preset_btn)
        preset_btn_layout.addWidget(self.save_preset_btn)

        # 预设列表
        self.preset_list = QListWidget()
        self.preset_list.itemClicked.connect(self.on_preset_item_clicked)
        self.preset_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.preset_list.customContextMenuRequested.connect(self.show_preset_context_menu)

        # 添加到预设布局
        preset_layout.addLayout(preset_btn_layout)
        preset_layout.addWidget(self.preset_list, 1)

        parent.addTab(preset_widget, "发送预设")

    def refresh_serial_ports(self):
        """刷新串口列表"""
        self.port_combo.clear()
        ports = SerialConfig.get_available_ports()
        for port in ports:
            self.port_combo.addItem(port)

    def open_serial(self):
        """打开串口"""
        try:
            # 获取选中的串口
            port_text = self.port_combo.currentText()
            if not port_text:
                QMessageBox.warning(self, "警告", "请选择串口")
                return False

            port_name = port_text.split(" - ")[0]

            # 获取串口参数
            baudrate = int(self.baudrate_combo.currentText())

            # 数据位映射
            databits_map = SerialConfig.get_databits_map()
            databits = databits_map[self.databits_combo.currentText()]

            # 校验位映射
            parity_map = SerialConfig.get_parity_map()
            parity = parity_map[self.parity_combo.currentText()]

            # 停止位映射
            stopbits_map = SerialConfig.get_stopbits_map()
            stopbits = stopbits_map[self.stopbits_combo.currentText()]

            # 打开串口
            self.serial_port = SerialConfig.open_serial_port(
                port_name, baudrate, databits, parity, stopbits
            )

            if self.serial_port.is_open:
                # 启动接收线程
                self.serial_thread = SerialThread(
                    self.serial_port,
                    self.hex_receive_check.isChecked(),
                    SerialConfig.get_encoding_value(self.receive_encoding_combo.currentText()),
                    SerialConfig.get_error_handling_value(self.error_handling_combo.currentText())
                )
                self.serial_thread.data_received.connect(lambda data: self.display_data(data, is_sent=False))
                self.serial_thread.error_occurred.connect(self.show_error)
                self.serial_thread.start()

                self.display_data(f"串口 {port_name} 已打开，波特率 {baudrate}\n")
                return True
            else:
                QMessageBox.warning(self, "警告", "无法打开串口")
                return False

        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开串口失败: {str(e)}")
            return False

    def close_serial(self):
        """关闭当前连接"""
        # 停止接收线程
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread = None

        # 使用connection_manager关闭当前连接
        current_conn = self.connection_manager.get_current_connection()
        if current_conn and current_conn.is_connected:
            conn_type = current_conn.connection_type
            self.connection_manager.disconnect()
            self.display_data(f"{conn_type}连接已关闭\n")
        
        # 停止文件发送线程
        if self.file_send_thread and self.file_send_thread.isRunning():
            self.file_send_thread.stop()
            self.file_send_thread = None

        # 停止定时发送
        if self.timer.isActive():
            self.timer.stop()
        
        # 重置serial_port引用（保持向后兼容）
        self.serial_port = None

    def append_received_data(self, data):
        """添加接收到的数据到显示区域"""
        # 注意：这个方法接收的是已经格式化的字符串数据
        # 实际的原始字节数据存储在DataReceiveThread中处理
        
        # 移动到文本末尾
        cursor = self.receive_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        current_theme = ThemeManager.get_theme()

        # 如果需要显示时间戳
        if self.timestamp_check.isChecked():
            current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
            time_format = QTextCharFormat()
            time_format.setForeground(QColor(current_theme["INFO"]))
            time_format.setFontWeight(QFont.Bold)
            cursor.insertText(f"[{current_time}] ", time_format)

        # 显示"收到"标记
        received_tag_format = QTextCharFormat()
        received_tag_format.setForeground(QColor(current_theme["INFO"]))
        received_tag_format.setFontWeight(QFont.Bold)
        cursor.insertText("[收到] ", received_tag_format)

        # 插入接收的数据
        data_format = QTextCharFormat()
        data_format.setForeground(QColor(current_theme["DARK"]))
        cursor.insertText(data, data_format)

        # 如果需要自动换行
        if self.newline_check.isChecked() and not data.endswith('\n'):
            cursor.insertText('\n')

        # 保持滚动到最底部
        self.receive_text.setTextCursor(cursor)
        self.receive_text.ensureCursorVisible()
    
    def append_raw_received_data(self, raw_data, timestamp=None):
        """添加原始接收数据到历史记录并显示"""
        if timestamp is None:
            timestamp = QDateTime.currentDateTime()
        
        # 存储原始数据到历史记录
        self.data_history.append({
            'raw_data': raw_data,
            'timestamp': timestamp,
            'is_sent': False
        })
        
        # 格式化并显示数据
        formatted_data = self._format_data(raw_data, 
                                         self.hex_receive_check.isChecked(),
                                         SerialConfig.get_encoding_value(self.receive_encoding_combo.currentText()),
                                         SerialConfig.get_error_handling_value(self.error_handling_combo.currentText()))
        
        self.append_received_data(formatted_data)
    
    def _format_data(self, raw_data, hex_mode, encoding, error_handling):
        """格式化原始数据"""
        if hex_mode:
            # 转换为十六进制字符串
            return ' '.join([f'{b:02X}' for b in raw_data]) + ' '
        else:
            # 转换为字符串（使用指定编码）
            return raw_data.decode(encoding, errors=error_handling)
    
    def _refresh_display(self):
        """重新格式化并显示所有历史数据"""
        # 保存当前滚动位置
        scrollbar = self.receive_text.verticalScrollBar()
        scroll_position = scrollbar.value()

        current_theme = ThemeManager.get_theme()
        
        # 清空显示区域
        self.receive_text.clear()
        
        # 重新显示所有历史数据
        for entry in self.data_history:
            cursor = self.receive_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            
            # 显示时间戳
            if self.timestamp_check.isChecked():
                time_str = entry['timestamp'].toString("yyyy-MM-dd HH:mm:ss.zzz")
                time_format = QTextCharFormat()
                time_format.setForeground(QColor(current_theme["INFO"]))
                time_format.setFontWeight(QFont.Bold)
                cursor.insertText(f"[{time_str}] ", time_format)
            
            # 显示标记
            tag_format = QTextCharFormat()
            tag_format.setForeground(QColor(current_theme["INFO"]))
            tag_format.setFontWeight(QFont.Bold)
            if entry['is_sent']:
                cursor.insertText("[发送] ", tag_format)
            else:
                cursor.insertText("[收到] ", tag_format)
            
            # 格式化并显示数据
            if entry['is_sent']:
                # 发送的数据直接显示（已经是字符串格式）
                data_format = QTextCharFormat()
                data_format.setForeground(QColor(current_theme["SUCCESS"]))
                cursor.insertText(entry['raw_data'], data_format)
            else:
                # 接收的数据需要重新格式化
                formatted_data = self._format_data(
                    entry['raw_data'],
                    self.hex_receive_check.isChecked(),
                    SerialConfig.get_encoding_value(self.receive_encoding_combo.currentText()),
                    SerialConfig.get_error_handling_value(self.error_handling_combo.currentText())
                )
                data_format = QTextCharFormat()
                data_format.setForeground(QColor(current_theme["DARK"]))
                cursor.insertText(formatted_data, data_format)
            
            # 添加换行
            if self.newline_check.isChecked():
                cursor.insertText('\n')
            
            self.receive_text.setTextCursor(cursor)
        
        # 恢复滚动位置
        scrollbar.setValue(scroll_position)
        self.receive_text.ensureCursorVisible()

    def display_data(self, data, is_sent=False):
        """显示数据（区分发送和接收）"""
        cursor = self.receive_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        current_theme = ThemeManager.get_theme()

        # 时间戳
        if self.timestamp_check.isChecked():
            current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
            time_format = QTextCharFormat()
            time_format.setForeground(QColor(current_theme["INFO"]))
            time_format.setFontWeight(QFont.Bold)
            cursor.insertText(f"[{current_time}] ", time_format)

        # 显示"发送"或"收到"标记
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor(current_theme["INFO"]))
        tag_format.setFontWeight(QFont.Bold)
        if is_sent:
            cursor.insertText("[发送] ", tag_format)
        else:
            cursor.insertText("[收到] ", tag_format)

        # 数据样式（发送的数据用不同颜色）
        data_format = QTextCharFormat()
        if is_sent:
            data_format.setForeground(QColor(current_theme["SUCCESS"]))  # 发送数据用成功色
        else:
            data_format.setForeground(QColor(current_theme["DARK"]))  # 接收数据用默认色

        cursor.insertText(data)
        self.receive_text.setTextCursor(cursor)
        self.receive_text.ensureCursorVisible()

    def send_data(self):
        """发送数据（支持定时发送）"""
        # 检查当前是否有活动连接
        current_conn = self.connection_manager.get_current_connection()
        if not current_conn or not current_conn.is_connected:
            QMessageBox.warning(self, "警告", "请先建立连接！")
            return

        # 从QTextEdit获取纯文本（支持换行符）
        data = self.send_text.toPlainText()
        if not data and not self.timed_send_check.isChecked():
            # 定时发送时允许发送空数据，手动发送时不允许
            return

        # 发送时清空接收区（如果勾选）
        if self.clear_on_send_check.isChecked():
            self.receive_text.clear()

        try:
            # 处理十六进制发送
            if self.hex_send_check.isChecked():
                # 移除所有空格
                data = data.replace(" ", "")
                # 转换为字节
                send_bytes = bytes.fromhex(data)
            else:
                # 处理编码
                encoding = SerialConfig.get_encoding_value(self.send_encoding_combo.currentText())
                # 处理换行符
                if self.append_newline_check.isChecked():
                    data += "\r\n"
                send_bytes = data.encode(encoding, errors="replace")

            # 发送数据（使用connection_manager）
            bytes_sent = self.connection_manager.send_data(send_bytes)
            if bytes_sent == 0:
                raise ConnectionError("发送失败，可能是连接已断开")

            # 记录发送历史（非定时发送时）
            if data and not self.timed_send_check.isChecked():
                self.send_history.append(data)
                self.history_index = len(self.send_history)

            # 在接收区显示发送的数据（带发送标识）
            self.display_data(f"{data}\n", is_sent=True)

            # 检查是否需要发送后清空发送框
            if self.clear_after_send_check.isChecked() and not self.timed_send_check.isChecked():
                self.send_text.clear()

        except ConnectionError as e:
            QMessageBox.critical(self, "连接错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送失败: {str(e)}")

    def toggle_hex_receive(self):
        """切换十六进制接收模式"""
        if self.serial_thread:
            self.serial_thread.update_settings(hex_mode=self.hex_receive_check.isChecked())
        # 重新格式化并显示所有历史数据
        self._refresh_display()

    def on_receive_encoding_changed(self):
        """接收编码改变时更新"""
        if self.serial_thread:
            encoding = SerialConfig.get_encoding_value(self.receive_encoding_combo.currentText())
            self.serial_thread.update_settings(encoding=encoding)
        # 重新格式化并显示所有历史数据
        self._refresh_display()

    def on_error_handling_changed(self):
        """错误处理方式改变时更新"""
        if self.serial_thread:
            error_handling = SerialConfig.get_error_handling_value(self.error_handling_combo.currentText())
            self.serial_thread.update_settings(error_handling=error_handling)

    def toggle_timed_send(self, state):
        """切换定时发送状态"""
        self.interval_spin.setEnabled(state)
        if state:
            # 检查是否已连接
            current_conn = self.connection_manager.get_current_connection()
            if not current_conn or not current_conn.is_connected:
                QMessageBox.warning(self, "警告", "请先建立连接！")
                # 自动取消勾选
                self.timed_send_check.blockSignals(True)
                self.timed_send_check.setChecked(False)
                self.timed_send_check.blockSignals(False)
                self.interval_spin.setEnabled(False)
                return
                
            # 启动定时器
            interval = self.interval_spin.value()
            self.timer.start(interval)
        else:
            # 停止定时器
            self.timer.stop()

    def search_text(self):
        """搜索文本"""
        search_text = self.search_input.text()
        if not search_text:
            return

        # 获取当前文本
        text = self.receive_text.toPlainText()
        # 设置搜索选项
        flags = Qt.CaseSensitive if self.search_case_sensitive.isChecked() else Qt.CaseInsensitive

        # 从上次位置开始搜索
        pos = self.last_search_pos
        index = text.indexOf(search_text, pos, flags)

        if index == -1:
            # 如果没找到，从头开始搜索
            index = text.indexOf(search_text, 0, flags)

        if index != -1:
            # 高亮显示找到的文本
            cursor = self.receive_text.textCursor()
            cursor.setPosition(index)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(search_text))
            self.receive_text.setTextCursor(cursor)
            self.receive_text.ensureCursorVisible()
            # 更新上次搜索位置
            self.last_search_pos = index + len(search_text)
        else:
            QMessageBox.information(self, "搜索", f"未找到 '{search_text}'")
            self.last_search_pos = 0

    def clear_receive_area(self):
        """清空接收区域"""
        self.receive_text.clear()
        # 同时清空历史数据记录
        self.data_history.clear()

    def save_received_data(self):
        """保存接收的数据"""
        if not self.receive_text.toPlainText():
            QMessageBox.information(self, "提示", "没有数据可保存")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存接收数据", "", "文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.receive_text.toPlainText())
                QMessageBox.information(self, "成功", f"数据已保存到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def send_file(self):
        """发送文件"""
        if not self.serial_port or not self.serial_port.is_open:
            QMessageBox.warning(self, "警告", "请先打开串口")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择要发送的文件", "", "所有文件 (*)"
        )

        if file_path:
            try:
                # 显示进度对话框
                progress = QProgressDialog("正在发送文件...", "取消", 0, 100, self)
                progress.setWindowTitle("文件发送")
                progress.setWindowModality(Qt.WindowModal)
                progress.setValue(0)

                # 创建并启动文件发送线程
                self.file_send_thread = FileSendThread(
                    self.serial_port,
                    file_path,
                    self.hex_send_check.isChecked(),
                    SerialConfig.get_encoding_value(self.send_encoding_combo.currentText())
                )
                self.file_send_thread.progress_updated.connect(progress.setValue)
                self.file_send_thread.finished.connect(self.on_file_send_finished)
                self.file_send_thread.finished.connect(progress.close)
                progress.canceled.connect(self.file_send_thread.stop)

                self.file_send_thread.start()
                progress.exec_()

            except Exception as e:
                QMessageBox.critical(self, "错误", f"文件发送准备失败: {str(e)}")

    def on_file_send_finished(self, success, message):
        """文件发送完成回调"""
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "失败", message)
        self.file_send_thread = None

    def set_rts(self):
        """设置RTS信号状态（读取复选框实际状态）"""
        if self.serial_port and self.serial_port.is_open:
            is_checked = self.rts_check.isChecked()  # 直接获取当前选中状态
            self.serial_port.rts = is_checked
            state_text = "开启" if is_checked else "关闭"
            self.display_data(f"RTS信号已{state_text}\n")

    def set_dtr(self):
        """设置DTR信号状态（读取复选框实际状态）"""
        if self.serial_port and self.serial_port.is_open:
            is_checked = self.dtr_check.isChecked()  # 直接获取当前选中状态
            self.serial_port.dtr = is_checked
            state_text = "开启" if is_checked else "关闭"
            self.display_data(f"DTR信号已{state_text}\n")

    def browse_file(self):
        """打开文件选择对话框，选择要发送的文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要发送的文件",
            "",
            "所有文件 (*);;文本文件 (*.txt);;二进制文件 (*.bin)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)

    def show_history(self):
        """显示发送历史记录对话框"""
        current_theme = ThemeManager.get_theme()
        if not self.send_history:
            QMessageBox.information(self, "历史记录", "暂无发送历史记录")
            return

        # 创建历史记录对话框
        dialog = QWidget(self)
        dialog.setWindowTitle("发送历史记录")
        dialog.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout(dialog)

        # 创建带边框的历史记录容器
        history_group = GradientGroupBox("历史记录管理")
        history_group_layout = QVBoxLayout(history_group)

        # 添加提示信息
        hint_label = QLabel("双击项目加载到发送框，或使用下方按钮进行操作：")
        hint_label.setStyleSheet(f"color: {current_theme['DARK']}; padding: 5px;")
        history_group_layout.addWidget(hint_label)

        # 创建历史记录列表
        history_list = QListWidget()
        for i, item in enumerate(reversed(self.send_history)):  # 倒序显示，最新的在上面
            list_item = QListWidgetItem(f"[{i + 1}] {item[:50]}{'...' if len(item) > 50 else ''}")
            list_item.setData(Qt.UserRole, item)  # 存储完整内容
            history_list.addItem(list_item)

        # 双击历史项时加载到发送框
        def load_history_item():
            selected = history_list.currentItem()
            if selected:
                # 给QTextEdit设置历史文本（保留换行）
                self.send_text.setPlainText(selected.data(Qt.UserRole))

        history_list.itemDoubleClicked.connect(load_history_item)
        history_group_layout.addWidget(history_list)

        # 按钮布局
        btn_layout = QHBoxLayout()
        load_btn = HoverButton("加载选中项")
        load_btn.clicked.connect(load_history_item)
        self.buttons.append(load_btn)  # 添加到按钮列表以便主题更新

        clear_btn = HoverButton("清空历史")
        self.buttons.append(clear_btn)

        def clear_history():
            if QMessageBox.question(dialog, "确认", "确定要清空所有发送历史吗？") == QMessageBox.Yes:
                self.send_history = []
                history_list.clear()

        clear_btn.clicked.connect(clear_history)

        close_btn = HoverButton("关闭")
        close_btn.clicked.connect(dialog.close)
        self.buttons.append(close_btn)

        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()

        history_group_layout.addLayout(btn_layout)
        layout.addWidget(history_group)

        dialog.setLayout(layout)
        dialog.show()

    def add_preset(self):
        """添加发送预设"""
        text, ok = QInputDialog.getMultiLineText(self, "添加预设", "请输入预设内容:")
        if ok and text:
            if self.preset_manager.add_preset(text):
                self.preset_list.addItem(self.preset_manager.get_preset_display_text(text))

    def edit_preset(self):
        """编辑选中的预设"""
        current_item = self.preset_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个预设")
            return

        index = self.preset_list.row(current_item)
        current_preset = self.preset_manager.get_preset(index)
        if current_preset:
            text, ok = QInputDialog.getMultiLineText(
                self, "编辑预设", "修改预设内容:", current_preset
            )
            if ok and text:
                if self.preset_manager.edit_preset(index, text):
                    current_item.setText(self.preset_manager.get_preset_display_text(text))

    def delete_preset(self):
        """删除选中的预设"""
        current_item = self.preset_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个预设")
            return

        index = self.preset_list.row(current_item)
        if self.preset_manager.delete_preset(index):
            self.preset_list.takeItem(index)

    def on_preset_item_clicked(self, item):
        """预设项被点击时"""
        index = self.preset_list.row(item)
        preset = self.preset_manager.get_preset(index)
        if preset:
            self.send_text.setText(preset)

    def show_preset_context_menu(self, position):
        """显示预设列表的右键菜单"""
        menu = QMenu()
        send_action = QAction("发送此预设", self)
        send_action.triggered.connect(self.send_selected_preset)
        menu.addAction(send_action)
        menu.exec_(self.preset_list.mapToGlobal(position))

    def send_selected_preset(self):
        """发送选中的预设"""
        current_item = self.preset_list.currentItem()
        if current_item:
            index = self.preset_list.row(current_item)
            preset = self.preset_manager.get_preset(index)
            if preset:
                self.send_text.setText(preset)
                self.send_data()

    def load_presets(self):
        """加载预设"""
        self.preset_list.clear()
        for preset in self.preset_manager.get_all_presets():
            self.preset_list.addItem(self.preset_manager.get_preset_display_text(preset))

    def load_presets_from_file(self):
        """从文件加载预设"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载预设", "", "预设文件 (*.preset);;所有文件 (*)"
        )
        if file_path:
            try:
                if self.preset_manager.load_presets_from_file(file_path):
                    self.preset_list.clear()
                    for preset in self.preset_manager.get_all_presets():
                        self.preset_list.addItem(self.preset_manager.get_preset_display_text(preset))
                    QMessageBox.information(self, "成功", f"已从 {file_path} 加载预设")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def save_presets_to_file(self):
        """将预设保存到文件"""
        if not self.preset_manager.get_all_presets():
            QMessageBox.information(self, "提示", "没有预设可保存")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存预设", "", "预设文件 (*.preset);;所有文件 (*)"
        )
        if file_path:
            try:
                if self.preset_manager.save_presets_to_file(file_path):
                    QMessageBox.information(self, "成功", f"预设已保存到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_error(self, message):
        """显示错误消息"""
        QMessageBox.critical(self, "错误", message)
        self.append_received_data(f"错误: {message}\n")

    def closeEvent(self, event):
        """窗口关闭时的处理"""
        self.close_serial()
        self.timer.stop()  # 停止定时器
        event.accept()
        
    def scan_bluetooth_devices(self):
        """扫描可用的蓝牙设备并显示在对话框中"""
        self.scan_bluetooth_btn.setText("扫描中... 🔍")
        self.scan_bluetooth_btn.setEnabled(False)
        
        # 使用蓝牙管理器进行设备扫描
        from bluetooth_manager import BluetoothManager
        
        # 创建蓝牙管理器实例
        if not hasattr(self, 'bluetooth_manager'):
            self.bluetooth_manager = BluetoothManager()
            # 连接信号
            self.bluetooth_manager.scan_finished.connect(self._show_bluetooth_devices)
            self.bluetooth_manager.scan_error.connect(self._handle_bluetooth_error)
        
        # 开始扫描
        self.bluetooth_manager.scan_devices()
    
    def _handle_bluetooth_error(self, error_message):
        """处理蓝牙扫描错误"""
        # 重置按钮状态
        self.scan_bluetooth_btn.setText("扫描设备 🔍")
        self.scan_bluetooth_btn.setEnabled(True)
        
        # 显示错误消息
        self.show_error(f"蓝牙扫描错误: {error_message}")
    
    def _show_bluetooth_devices(self, devices=None):
        """显示扫描到的蓝牙设备列表"""
        # 重置按钮状态
        self.scan_bluetooth_btn.setText("扫描设备 🔍")
        self.scan_bluetooth_btn.setEnabled(True)
        
        # 创建蓝牙设备列表对话框
        dialog = QWidget(self)
        dialog.setWindowTitle("可用蓝牙设备")
        dialog.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout(dialog)
        
        # 创建设备列表
        device_list = QListWidget()
        
        # 获取设备列表
        if devices is None and hasattr(self, 'bluetooth_manager'):
            devices = self.bluetooth_manager.get_devices()
        elif devices is None:
            # 如果没有设备列表，使用模拟数据
            from bluetooth_manager import BluetoothManager, BluetoothDevice
            self.bluetooth_manager = BluetoothManager()
            devices = self.bluetooth_manager.get_mock_devices()
        
        # 添加设备到列表
        if devices:
            for device in devices:
                item = QListWidgetItem(f"{device.name} [{device.address}]")
                item.setData(Qt.UserRole, device.address)
                device_list.addItem(item)
        else:
            item = QListWidgetItem("未找到蓝牙设备")
            device_list.addItem(item)
        
        # 双击选择设备
        def select_device():
            selected = device_list.currentItem()
            if selected:
                self.bluetooth_address_edit.setText(selected.data(Qt.UserRole))
                dialog.close()
        
        device_list.itemDoubleClicked.connect(select_device)
        
        # 创建按钮布局
        btn_layout = QHBoxLayout()
        
        # 创建退出按钮
        exit_btn = HoverButton("退出")
        exit_btn.clicked.connect(dialog.close)
        self.buttons.append(exit_btn)  # 添加到按钮列表以便主题更新
        
        # 创建选择按钮
        select_btn = HoverButton("选择设备")
        select_btn.clicked.connect(select_device)
        self.buttons.append(select_btn)  # 添加到按钮列表以便主题更新
        
        # 添加按钮到布局
        btn_layout.addWidget(exit_btn)
        btn_layout.addWidget(select_btn)
        
        # 添加到主布局
        layout.addWidget(device_list)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialMonitor()
    window.show()
    sys.exit(app.exec())


