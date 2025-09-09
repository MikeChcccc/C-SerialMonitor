import os

class PresetManager:
    def __init__(self, default_presets=None):
        self.presets = []
        self.default_presets = default_presets or [
            "Hello, World!",
            "Serial communication test",
            "1234567890"
        ]
        self.load_default_presets()
    
    def load_default_presets(self):
        """加载默认预设"""
        self.presets = self.default_presets.copy()
    
    def add_preset(self, preset_text):
        """添加预设"""
        if preset_text and preset_text not in self.presets:
            self.presets.append(preset_text)
            return True
        return False
    
    def edit_preset(self, index, new_text):
        """编辑预设"""
        if 0 <= index < len(self.presets) and new_text:
            self.presets[index] = new_text
            return True
        return False
    
    def delete_preset(self, index):
        """删除预设"""
        if 0 <= index < len(self.presets):
            del self.presets[index]
            return True
        return False
    
    def get_preset(self, index):
        """获取指定索引的预设"""
        if 0 <= index < len(self.presets):
            return self.presets[index]
        return None
    
    def get_all_presets(self):
        """获取所有预设"""
        return self.presets.copy()
    
    def load_presets_from_file(self, file_path):
        """从文件加载预设"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
                
            with open(file_path, 'r', encoding='utf-8') as f:
                self.presets = [line.rstrip('\n') for line in f]
            return True
        except Exception as e:
            raise Exception(f"加载预设失败: {str(e)}")
    
    def save_presets_to_file(self, file_path):
        """将预设保存到文件"""
        try:
            if not self.presets:
                raise ValueError("没有预设可保存")
                
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                for preset in self.presets:
                    f.write(preset + '\n')
            return True
        except Exception as e:
            raise Exception(f"保存预设失败: {str(e)}")
    
    def clear_all_presets(self):
        """清空所有预设"""
        self.presets = []
    
    def get_preset_display_text(self, preset_text):
        """获取预设的显示文本（截断过长的文本）"""
        return preset_text[:50] + "..." if len(preset_text) > 50 else preset_text