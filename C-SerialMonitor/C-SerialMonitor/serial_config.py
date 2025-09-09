import serial
from serial.tools import list_ports

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

class SerialConfig:
    @staticmethod
    def get_available_ports():
        """获取可用的串口列表"""
        ports = list_ports.comports()
        return [f"{port.device} - {port.description}" for port in ports]
    
    @staticmethod
    def get_default_baudrates():
        """获取默认的波特率列表"""
        return ["1200", "2400", "4800", "9600", "19200", "38400",
                "57600", "115200", "230400", "460800", "921600", "1500000"]
    
    @staticmethod
    def get_databits_map():
        """获取数据位映射表"""
        return {
            "5": serial.FIVEBITS,
            "6": serial.SIXBITS,
            "7": serial.SEVENBITS,
            "8": serial.EIGHTBITS
        }
    
    @staticmethod
    def get_parity_map():
        """获取校验位映射表"""
        return {
            "无": serial.PARITY_NONE,
            "奇校验": serial.PARITY_ODD,
            "偶校验": serial.PARITY_EVEN,
            "标记": serial.PARITY_MARK,
            "空格": serial.PARITY_SPACE
        }
    
    @staticmethod
    def get_stopbits_map():
        """获取停止位映射表"""
        return {
            "1": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO
        }
    
    @staticmethod
    def get_flowcontrol_map():
        """获取流控制映射表"""
        return {
            "无": 0,
            "硬件": 1,
            "软件": 2
        }
    
    @staticmethod
    def open_serial_port(port_name, baudrate, databits, parity, stopbits):
        """打开串口并返回串口对象"""
        try:
            serial_port = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=databits,
                parity=parity,
                stopbits=stopbits,
                timeout=0.1
            )
            return serial_port
        except Exception as e:
            raise Exception(f"打开串口失败: {str(e)}")
    
    @staticmethod
    def get_encoding_options():
        """获取所有编码选项"""
        return list(ENCODING_OPTIONS.keys())
    
    @staticmethod
    def get_encoding_value(name):
        """获取编码值"""
        return ENCODING_OPTIONS.get(name, "utf-8")
    
    @staticmethod
    def get_error_handling_options():
        """获取所有错误处理选项"""
        return list(ERROR_HANDLING_OPTIONS.keys())
    
    @staticmethod
    def get_error_handling_value(name):
        """获取错误处理值"""
        return ERROR_HANDLING_OPTIONS.get(name, "replace")