import time
import serial
from PySide6.QtCore import QThread, Signal, Qt

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
            file_size = self.get_file_size()
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

    def get_file_size(self):
        """获取文件大小"""
        import os
        try:
            return os.path.getsize(self.file_path)
        except:
            return 0