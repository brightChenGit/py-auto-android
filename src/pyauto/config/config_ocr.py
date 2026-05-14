# -*- coding: utf-8 -*-
import os
import sys
import json
import tempfile
from typing import Dict, Any
import pyauto.utils.logUtil

# 获取全局 logger 实例
logger = pyauto.utils.logUtil.get_logger()

def natural_sort_key(s):
    """用于自然排序的 Key 函数"""
    return [(int(text) if text.isdigit() else text.lower()) for text in re.split(r'(\d+)', s)]

class ConfigOcrManager:
    """
    优化版 OCR 配置管理器。
    功能：单例模式，支持开发环境与打包后 EXE 环境的路径自动适配，提供原子写入保护。
    """

    # --- 类变量：配置文件路径 ---
    # 1. 确定根目录：兼容 PyInstaller 打包后环境与开发环境
    if getattr(sys, 'frozen', False):
        _base_dir = os.path.dirname(sys.executable) # 打包后：与 exe 同级
    else:
        _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 开发时：项目根目录

    # 2. 构建配置文件完整路径
    CONFIG_FILE_PATH = os.path.join(_base_dir, "config", "config_ocr.json")

    # --- 实例变量 ---
    _instance = None
    _configs: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigOcrManager, cls).__new__(cls)
            cls._instance._load_configs()
        return cls._instance

    def _load_configs(self):
        """从 JSON 文件加载配置数据"""
        config_dir = os.path.dirname(self.CONFIG_FILE_PATH)

        # 确保目录存在
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
                logger.info(f"[Config] 创建配置目录：{config_dir}")
            except OSError as e:
                logger.error(f"[Config] 无法创建配置目录：{e}")
                self._configs = {}
                return

        # 读取文件
        if os.path.exists(self.CONFIG_FILE_PATH):
            try:
                with open(self.CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    self._configs = json.load(f)
                logger.debug(f"[Config] 成功加载配置：{self.CONFIG_FILE_PATH}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"[Config] 读取或解析失败：{e}")
                self._configs = {}
        else:
            # 文件不存在，初始化默认配置
            self._configs = {
                "use_cuda": False,
                "use_dml": False
            }
            self._save_configs() # 自动创建默认文件
            logger.info(f"[Config] 未找到配置文件，已生成默认配置：{self.CONFIG_FILE_PATH}")

    def _save_configs(self):
        """原子写入保存，防止文件损坏"""
        temp_path = None
        try:
            # 1. 创建临时文件
            fd, temp_path = tempfile.mkstemp(suffix='.tmp', prefix='config_', dir=os.path.dirname(self.CONFIG_FILE_PATH))

            # 2. 写入数据
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self._configs, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno()) # 确保写入磁盘

            # 3. 原子替换
            if os.path.exists(self.CONFIG_FILE_PATH):
                os.replace(temp_path, self.CONFIG_FILE_PATH)
            else:
                os.rename(temp_path, self.CONFIG_FILE_PATH)

        except Exception as e:
            logger.error(f"[Config] 保存失败：{e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    # --- 对外接口 ---

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        获取 OCR 引擎配置。
        :return: 包含 use_cuda, use_dml 等键值的字典
        """
        instance = cls()
        return instance._configs.copy() # 返回副本，防止外部直接修改内部状态

    @classmethod
    def set_config(cls, config_data: Dict[str, Any]):
        """
        保存 OCR 引擎配置。
        :param config_data: 配置字典
        """
        instance = cls()
        instance._configs.update(config_data) # 使用 update 允许部分更新
        instance._save_configs()