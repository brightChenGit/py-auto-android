# config/config_manager.py
import os
import re
import sys
import json
import tempfile
from typing import Dict, Any, OrderedDict
import pyauto.utils.logUtil

def natural_sort_key(s):
    """用于自然排序的 Key 函数"""
    return [(int(text) if text.isdigit() else text.lower()) for text in re.split(r'(\d+)', s)]

# 获取全局 logger 实例
logger =  pyauto.utils.logUtil.get_logger()

def get_config_root():
    """
    获取配置文件的根目录。
    兼容开发环境和打包后的 EXE 环境。
    策略：打包后使用 exe 所在目录，开发时使用项目根目录或当前脚本所在目录。
    """
    if getattr(sys, 'frozen', False):
        # 🔥 打包后：sys.executable 指向 exe 文件，配置应存放在 exe 同级目录
        return os.path.dirname(sys.executable)
    else:
        # 🛠️ 开发环境：
        # 选项 A: 存放在当前脚本所在目录 (config/)
        # return os.path.dirname(os.path.abspath(__file__))

        # 选项 B (推荐): 存放在项目根目录，方便管理 (假设当前文件在 config/ 下)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(current_dir)

class DeviceConfigManager:
    """
    管理所有设备的任务配置，支持任意 JSON 结构。
    """
    _base_dir = get_config_root()
    _config_dir=os.path.join(_base_dir, "config")
    CONFIG_FILE_PATH = os.path.join(_config_dir, "device_configs.json")

    _instance = None
    _configs: Dict[str, Dict] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeviceConfigManager, cls).__new__(cls)
            cls._instance._load_configs()
        return cls._instance

    def _load_configs(self):
        """从 JSON 文件加载配置"""
        config_dir = os.path.dirname(self.CONFIG_FILE_PATH)
        if config_dir and not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
            except OSError as e:
                logger.error(f"[Config] 无法创建配置目录：{e}")
                # 初始化为空有序字典
                self._configs = OrderedDict()
                return

        if os.path.exists(self.CONFIG_FILE_PATH):
            try:
                with open(self.CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        self._configs = OrderedDict()
                    else:
                        raw_data  = json.loads(content)
                        sorted_items = sorted(raw_data.items(), key=lambda item: natural_sort_key(item[0]))
                        self._configs = OrderedDict(sorted_items)
                    if not isinstance(self._configs, dict):
                        logger.info("[Config] 配置文件格式错误，已重置")
                        self._configs = OrderedDict()
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"[Config] 读取或解析失败：{e}")
                self._configs = OrderedDict()
        else:
            self._configs = OrderedDict()

    def _save_configs(self):
        """原子写入保存"""
        sorted_items = sorted(self._configs.items(), key=lambda item: natural_sort_key(item[0]))
        self._configs = OrderedDict(sorted_items)
        config_dir = os.path.dirname(self.CONFIG_FILE_PATH)
        if config_dir and not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
            except OSError:
                return

        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(suffix='.tmp', prefix='config_', dir=config_dir)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self._configs, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.CONFIG_FILE_PATH)
        except Exception as e:
            logger.error(f"[Config] 保存失败：{e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    @classmethod
    def get_config(cls, device_id: str) -> Dict[str, Any]:
        """获取指定设备的配置。若不存在，返回空的默认模板（可根据需要修改默认模板）"""
        instance = cls()
        if device_id not in instance._configs:
            # 默认模板可以是空的，也可以包含常用键，这里设为空字典以支持完全动态
            instance._configs[device_id] = {}
        return instance._configs[device_id]

    @classmethod
    def save_config(cls, device_id: str, config_data: Dict[str, Any]):
        """
        保存指定设备的完整配置字典。
        :param device_id: 设备ID
        :param config_data: 完整的配置字典 (可以是任意 Key-Value 结构)
        """
        instance = cls()
        instance._configs[device_id] = config_data
        instance._save_configs()

    @classmethod
    def get_all_device_ids(cls) -> list:
        instance = cls()
        return sorted(instance._configs.keys(), key=natural_sort_key)