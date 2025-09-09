import time
import threading
import asyncio
from PySide6.QtCore import QObject, Signal

class BluetoothError(Exception):
    """蓝牙相关的异常类"""
    pass

class BluetoothDevice:
    """蓝牙设备信息类"""
    def __init__(self, name, address):
        self.name = name
        self.address = address
        
    def __str__(self):
        return f"{self.name} [{self.address}]"

class BluetoothManager(QObject):
    """蓝牙管理器，处理设备扫描和连接"""
    # 定义信号
    scan_started = Signal()
    scan_finished = Signal(list)  # 参数为设备列表
    scan_error = Signal(str)      # 参数为错误信息
    
    def __init__(self):
        super().__init__()
        self.devices = []
        self.scanning = False
        self.scan_thread = None
        self._initialize_bluetooth()
        
    def _initialize_bluetooth(self):
        """初始化蓝牙模块"""
        self.bluetooth_available = False
        self.using_bleak = False
        
        # 首先尝试导入PyBluez
        try:
            import bluetooth
            self.bluetooth = bluetooth
            self.bluetooth_available = True
            print("已加载PyBluez库")
            return
        except ImportError:
            print("未找到PyBluez库，尝试加载Bleak...")
        
        # 如果PyBluez不可用，尝试导入Bleak
        try:
            import bleak
            self.bleak = bleak
            self.bluetooth_available = True
            self.using_bleak = True
            print("已加载Bleak库")
        except ImportError:
            print("警告: 未安装蓝牙库(PyBluez或Bleak)，将使用模拟模式")
            self.bluetooth = None
            self.bleak = None
            
    def is_bluetooth_available(self):
        """检查蓝牙功能是否可用"""
        return self.bluetooth_available
    
    def get_mock_devices(self):
        """获取模拟的蓝牙设备列表（用于演示）"""
        return [
            BluetoothDevice("HC-05蓝牙模块", "00:11:22:33:44:55"),
            BluetoothDevice("Arduino Nano 33 BLE", "11:22:33:44:55:66"),
            BluetoothDevice("ESP32 BLE", "22:33:44:55:66:77"),
            BluetoothDevice("蓝牙耳机", "33:44:55:66:77:88"),
            BluetoothDevice("未知设备", "44:55:66:77:88:99")
        ]
    
    def scan_devices(self):
        """扫描可用的蓝牙设备"""
        if self.scanning:
            return False
            
        self.scanning = True
        self.scan_started.emit()
        
        # 创建并启动扫描线程
        self.scan_thread = threading.Thread(target=self._scan_thread_func)
        self.scan_thread.daemon = True
        self.scan_thread.start()
        return True
        
    def _scan_thread_func(self):
        """蓝牙扫描线程函数"""
        try:
            if self.bluetooth_available:
                if self.using_bleak:
                    # 使用Bleak库扫描设备
                    self.devices = self._scan_with_bleak()
                else:
                    # 使用PyBluez库扫描设备
                    discovered_devices = self.bluetooth.discover_devices(
                        duration=8,  # 扫描时间（秒）
                        lookup_names=True,  # 同时获取设备名称
                        flush_cache=True,   # 刷新缓存
                        lookup_class=False  # 不获取设备类别
                    )
                    
                    # 转换为BluetoothDevice对象列表
                    self.devices = []
                    for addr, name in discovered_devices:
                        if not name:  # 如果没有获取到名称
                            name = "未知设备"
                        self.devices.append(BluetoothDevice(name, addr))
            else:
                # 使用模拟设备
                time.sleep(2)  # 模拟扫描延迟
                self.devices = self.get_mock_devices()
                
            # 扫描完成，发送信号
            self.scan_finished.emit(self.devices)
        except Exception as e:
            self.scan_error.emit(str(e))
        finally:
            self.scanning = False
            
    def _scan_with_bleak(self):
        """使用Bleak库扫描BLE设备"""
        devices = []
        
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 定义异步扫描函数
        async def scan():
            scanner = self.bleak.BleakScanner()
            discovered_devices = await scanner.discover(timeout=8.0)
            return discovered_devices
        
        # 运行扫描
        discovered_devices = loop.run_until_complete(scan())
        
        # 转换为BluetoothDevice对象列表
        for device in discovered_devices:
            name = device.name if device.name else "未知BLE设备"
            devices.append(BluetoothDevice(name, device.address))
            
        return devices
    
    def get_devices(self):
        """获取已扫描到的设备列表"""
        return self.devices
    
    def create_bluetooth_socket(self, address, port=1):
        """创建蓝牙套接字连接"""
        if not self.bluetooth_available:
            raise BluetoothError("蓝牙功能不可用，请安装pybluez或bleak库")
            
        try:
            if self.using_bleak:
                # 使用Bleak创建连接
                # 注意：Bleak使用异步API，这里返回一个包装器
                return self._create_bleak_client(address)
            else:
                # 使用PyBluez创建连接
                socket = self.bluetooth.BluetoothSocket(self.bluetooth.RFCOMM)
                socket.connect((address, port))
                return socket
        except Exception as e:
            raise BluetoothError(f"蓝牙连接失败: {str(e)}")
            
    def _create_bleak_client(self, address):
        """创建Bleak客户端连接包装器"""
        # 创建一个包装Bleak客户端的对象，模拟socket接口
        class BleakClientWrapper:
            def __init__(self, address, bleak_module):
                self.address = address
                self.bleak = bleak_module
                self.client = None
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.connected = False
                
                # 连接设备
                self.client = self.loop.run_until_complete(self._connect())
                self.connected = True
                
            async def _connect(self):
                client = self.bleak.BleakClient(self.address)
                await client.connect()
                return client
                
            def close(self):
                if self.client and self.connected:
                    self.loop.run_until_complete(self.client.disconnect())
                    self.connected = False
                    
            def send(self, data):
                if not self.client or not self.connected:
                    return 0
                    
                # 查找可写特征
                for service in self.client.services:
                    for char in service.characteristics:
                        if "write" in char.properties:
                            self.loop.run_until_complete(self.client.write_gatt_char(char.uuid, data))
                            return len(data)
                return 0
                
            def recv(self, bufsize):
                # 注意：这是一个简化实现，实际应用中可能需要更复杂的通知处理
                if not self.client or not self.connected:
                    return b''
                    
                # 这里应该实现从通知中读取数据的逻辑
                # 由于BLE通信通常基于通知，这里只是一个占位符
                return b''
                
            def settimeout(self, timeout):
                # BLE客户端没有直接的超时设置，这里是一个占位符
                pass
                
        return BleakClientWrapper(address, self.bleak)