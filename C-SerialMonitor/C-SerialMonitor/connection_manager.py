import serial
import socket
import time
import threading
import serial
from PySide6.QtCore import QThread, Signal, Qt

class ConnectionError(Exception):
    """连接相关的异常类"""
    pass

class Connection:
    """连接基类，定义通用接口"""
    def __init__(self):
        self.is_connected = False
        self.connection_type = "Unknown"
        self.settings = {}
        
    def connect(self):
        """建立连接"""
        raise NotImplementedError("子类必须实现connect方法")
        
    def disconnect(self):
        """断开连接"""
        raise NotImplementedError("子类必须实现disconnect方法")
        
    def send(self, data):
        """发送数据"""
        raise NotImplementedError("子类必须实现send方法")
        
    def receive(self):
        """接收数据"""
        raise NotImplementedError("子类必须实现receive方法")
        
    def get_info(self):
        """获取连接信息"""
        return f"{self.connection_type} Connection"

class SerialConnection(Connection):
    """串口连接实现"""
    def __init__(self, port_name, baudrate, databits=8, parity=serial.PARITY_NONE, stopbits=1):
        super().__init__()
        self.connection_type = "Serial"
        self.port_name = port_name
        self.baudrate = baudrate
        self.databits = databits
        self.parity = parity
        self.stopbits = stopbits
        self.serial_port = None
        
    def connect(self):
        try:
            self.serial_port = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                bytesize=self.databits,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=0.1
            )
            self.is_connected = self.serial_port.is_open
            return self.is_connected
        except Exception as e:
            raise ConnectionError(f"串口连接失败: {str(e)}")
            
    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.is_connected = False
            
    def send(self, data):
        if self.serial_port and self.serial_port.is_open:
            return self.serial_port.write(data)
        return 0
        
    def receive(self):
        if self.serial_port and self.serial_port.is_open:
            # 尝试读取最多4096字节的数据
            try:
                # 先检查是否有数据等待
                if self.serial_port.in_waiting:
                    return self.serial_port.read(self.serial_port.in_waiting)
                # 如果没有数据等待，直接尝试读取一小部分数据，这样可以在TX/RX短接时捕获回环数据
                # 设置超时时间为0.01秒，避免长时间阻塞
                return self.serial_port.read(4096) or b''
            except Exception:
                return b''
        return b''
        
    def get_info(self):
        return f"串口 {self.port_name}，波特率 {self.baudrate}"

class TCPConnection(Connection):
    """TCP/IP连接实现"""
    def __init__(self, host, port, is_server=False):
        super().__init__()
        self.connection_type = "TCP"
        self.host = host
        self.port = port
        self.is_server = is_server
        self.socket = None
        self.client_socket = None
        self.server_thread = None
        
    def connect(self):
        try:
            if self.is_server:
                # 服务器模式
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind((self.host, self.port))
                self.socket.listen(1)
                self.is_connected = True
                # 创建接受客户端连接的线程
                self.server_thread = threading.Thread(target=self._accept_client)
                self.server_thread.daemon = True
                self.server_thread.start()
                return True
            else:
                # 客户端模式
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                self.is_connected = True
                return True
        except Exception as e:
            raise ConnectionError(f"TCP连接失败: {str(e)}")
            
    def _accept_client(self):
        """接受客户端连接的线程函数"""
        while self.is_connected and self.socket:
            try:
                # 设置超时，以便能够定期检查是否应该停止线程
                self.socket.settimeout(1.0)
                client, addr = self.socket.accept()
                # 关闭之前的客户端连接（如果有）
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except:
                        pass
                self.client_socket = client
                print(f"客户端已连接: {addr}")
            except socket.timeout:
                # 超时，继续循环
                pass
            except OSError as e:
                # 套接字错误，可能是套接字已关闭
                if self.is_connected:  # 只有在仍然应该连接时才打印错误
                    print(f"接受客户端连接时出错: {e}")
                break
            except Exception as e:
                # 其他错误
                if self.is_connected:  # 只有在仍然应该连接时才打印错误
                    print(f"接受客户端连接时出错: {e}")
                break
    
    def disconnect(self):
        # 先设置标志，让接受线程退出
        self.is_connected = False
        
        # 关闭客户端套接字
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            
        # 关闭服务器套接字
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            
        # 等待服务器线程结束
        if self.server_thread and self.server_thread.is_alive():
            try:
                self.server_thread.join(2.0)  # 最多等待2秒
            except:
                pass
            self.server_thread = None
        
    def send(self, data):
        if self.is_server and self.client_socket:
            return self.client_socket.send(data)
        elif not self.is_server and self.socket:
            return self.socket.send(data)
        return 0
        
    def receive(self):
        if self.is_server and self.client_socket:
            try:
                # 设置非阻塞模式
                self.client_socket.setblocking(False)
                data = self.client_socket.recv(4096)
                return data
            except BlockingIOError:
                return b''
            except Exception:
                return b''
        elif not self.is_server and self.socket:
            try:
                # 设置非阻塞模式
                self.socket.setblocking(False)
                data = self.socket.recv(4096)
                return data
            except BlockingIOError:
                return b''
            except Exception:
                return b''
        return b''
        
    def get_info(self):
        mode = "服务器" if self.is_server else "客户端"
        return f"TCP {mode} {self.host}:{self.port}"

class UDPConnection(Connection):
    """UDP连接实现"""
    def __init__(self, local_host, local_port, remote_host=None, remote_port=None):
        super().__init__()
        self.connection_type = "UDP"
        self.local_host = local_host
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.socket = None
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.local_host, self.local_port))
            self.is_connected = True
            # 如果指定了远程地址，可以设置默认发送目标
            if self.remote_host and self.remote_port:
                self.socket.connect((self.remote_host, self.remote_port))
            return True
        except Exception as e:
            raise ConnectionError(f"UDP连接失败: {str(e)}")
            
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.is_connected = False
        
    def send(self, data, remote_host=None, remote_port=None):
        if self.socket:
            if remote_host and remote_port:
                return self.socket.sendto(data, (remote_host, remote_port))
            elif self.remote_host and self.remote_port:
                return self.socket.send(data)
        return 0
        
    def receive(self):
        if self.socket:
            try:
                # 设置非阻塞模式
                self.socket.setblocking(False)
                data, addr = self.socket.recvfrom(4096)
                return data
            except BlockingIOError:
                return b''
            except Exception:
                return b''
        return b''
        
    def get_info(self):
        if self.remote_host and self.remote_port:
            return f"UDP {self.local_host}:{self.local_port} -> {self.remote_host}:{self.remote_port}"
        return f"UDP {self.local_host}:{self.local_port}"

class WiFiConnection(TCPConnection):
    """WiFi连接实现（基于TCP）"""
    def __init__(self, host, port, is_server=False):
        super().__init__(host, port, is_server)
        self.connection_type = "WiFi"
        
    def get_info(self):
        mode = "服务器" if self.is_server else "客户端"
        return f"WiFi {mode} {self.host}:{self.port}"

class EthernetConnection(TCPConnection):
    """以太网连接实现（基于TCP）"""
    def __init__(self, host, port, is_server=False):
        super().__init__(host, port, is_server)
        self.connection_type = "Ethernet"
        
    def get_info(self):
        mode = "服务器" if self.is_server else "客户端"
        return f"以太网 {mode} {self.host}:{self.port}"

# 蓝牙连接实现（使用bluetooth_manager模块）
class BluetoothConnection(Connection):
    """蓝牙连接实现"""
    def __init__(self, address, port=1):
        super().__init__()
        self.connection_type = "Bluetooth"
        self.address = address
        self.port = port
        self.socket = None
        
        # 导入蓝牙管理器
        from bluetooth_manager import BluetoothManager, BluetoothError
        self.bt_manager = BluetoothManager()
        self.BluetoothError = BluetoothError
        
    def connect(self):
        try:
            if not self.bt_manager.is_bluetooth_available():
                raise ConnectionError("请安装pybluez库以支持蓝牙功能")
                
            # 使用蓝牙管理器创建连接
            self.socket = self.bt_manager.create_bluetooth_socket(self.address, self.port)
            self.is_connected = True
            return True
        except self.BluetoothError as e:
            raise ConnectionError(str(e))
        except Exception as e:
            raise ConnectionError(f"蓝牙连接失败: {str(e)}")
            
    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.is_connected = False
        
    def send(self, data):
        if self.socket and self.is_connected:
            try:
                return self.socket.send(data)
            except:
                return 0
        return 0
        
    def receive(self):
        if self.socket and self.is_connected:
            try:
                # 设置非阻塞模式
                self.socket.settimeout(0.1)
                data = self.socket.recv(4096)
                return data
            except Exception:
                return b''
        return b''
        
    def get_info(self):
        return f"蓝牙 {self.address}:{self.port}"

class ConnectionManager:
    """连接管理器，管理各种连接类型"""
    def __init__(self):
        self.current_connection = None
        self.connections = {}
        
    def create_connection(self, connection_type, **kwargs):
        """创建连接"""
        connection_types = {
            "serial": SerialConnection,
            "tcp": TCPConnection,
            "udp": UDPConnection,
            "wifi": WiFiConnection,
            "ethernet": EthernetConnection,
            "bluetooth": BluetoothConnection
        }
        
        if connection_type.lower() not in connection_types:
            raise ValueError(f"不支持的连接类型: {connection_type}")
        
        connection = connection_types[connection_type.lower()](**kwargs)
        self.connections[connection.get_info()] = connection
        self.current_connection = connection
        return connection
        
    def connect(self):
        """建立当前连接"""
        if self.current_connection:
            return self.current_connection.connect()
        return False
        
    def disconnect(self):
        """断开当前连接"""
        if self.current_connection:
            self.current_connection.disconnect()
            
    def send_data(self, data):
        """发送数据"""
        if self.current_connection and self.current_connection.is_connected:
            return self.current_connection.send(data)
        return 0
        
    def get_current_connection(self):
        """获取当前连接"""
        return self.current_connection
        
    def get_connection_info(self):
        """获取当前连接信息"""
        if self.current_connection:
            return self.current_connection.get_info()
        return "未连接"

# 通用数据接收线程
class DataReceiveThread(QThread):
    """数据接收线程"""
    data_received = Signal(str)  # 保留兼容性
    raw_data_received = Signal(bytes)  # 新增原始数据信号
    error_occurred = Signal(str)
    
    def __init__(self, connection, hex_mode=False, encoding="utf-8", error_handling="replace"):
        super().__init__()
        self.connection = connection
        self.running = False
        self.hex_mode = hex_mode
        self.encoding = encoding
        self.error_handling = error_handling
        
    def run(self):
        self.running = True
        while self.running and self.connection and self.connection.is_connected:
            try:
                # 接收数据
                data = self.connection.receive()
                
                if data:
                    # 发送原始字节数据
                    self.raw_data_received.emit(data)
                    
                    # 为了兼容性，也发送格式化后的数据
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
        """更新接收设置"""
        if hex_mode is not None:
            self.hex_mode = hex_mode
        if encoding is not None:
            self.encoding = encoding
        if error_handling is not None:
            self.error_handling = error_handling