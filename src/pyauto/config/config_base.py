# -*- coding: utf-8 -*-
import os
import sys
import json
import tempfile
import re
from typing import Dict, Any
import pyauto.utils.logUtil
# 注意：请确保你的环境中包含 pyauto 库，或者替换为你实际使用的日志库
try:
    logger = pyauto.utils.logUtil.get_logger()
except ImportError:
    # 简单的回退日志配置，防止报错
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def natural_sort_key(s):
    """用于自然排序的 Key 函数"""
    return [(int(text) if text.isdigit() else text.lower()) for text in re.split(r'(\d+)', s)]

class UnifiedConfigManager:
    """
    统一配置管理器
    功能：
    1. 合并 OCR 和 Base 配置到单一入口。
    2. 单例模式，确保全局配置状态一致。
    3. 支持开发环境与打包后 EXE 环境的路径自动适配。
    4. 提供原子写入保护，防止文件损坏。
    """

    # --- 类变量 ---
    _instance = None
    _configs: Dict[str, Any] = {}

    # 1. 确定根目录：兼容 PyInstaller 打包后环境与开发环境
    if getattr(sys, 'frozen', False):
        _base_dir = os.path.dirname(sys.executable) # 打包后：与 exe 同级
    else:
        _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 开发时：项目根目录

    # 2. 构建配置文件完整路径 (统一为一个文件 config.json)
    CONFIG_FILE_PATH = os.path.join(_base_dir, "config", "config_base.json")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UnifiedConfigManager, cls).__new__(cls)
            cls._instance._load_configs()
        return cls._instance

    def _load_configs(self):
        """从 JSON 文件加载配置数据，若不存在则生成默认合并配置"""
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
                logger.error(f"[Config] 读取或解析失败：{e}，将使用默认配置覆盖。")
                self._configs = self._get_default_configs()
                self._save_configs()
        else:
            # 文件不存在，初始化默认配置
            self._configs = self._get_default_configs()
            self._save_configs()
            logger.info(f"[Config] 未找到配置文件，已生成默认配置：{self.CONFIG_FILE_PATH}")

    def _get_default_configs(self) -> Dict[str, Any]:
        """定义默认的合并配置结构"""
        return {
            # --- 其他基础配置 ---
            "local_name": os.environ.get('COMPUTERNAME') or os.uname().nodename,
            "bool_auto_stop": False,
            # --- OCR 配置部分 ---
            "ocr": {
                "use_cuda": False,
                "use_dml": False
            },
            # --- 基础/邮件 配置部分 ---
            "email": {
                "smtp_host": "smtp.qq.com",
                "smtp_port": "465",
                "sender_email": "your_email@qq.com",
                "auth_code": "",
                "receiver_email": "your_email@qq.com",
                "task_start": True,
                "task_end": True,
                "task_error": True,
                "task_manual": True,
                "task_captcha":True
            },
            "mysql": {
                "host": "localhost",
                "port": "3306",
                "user": "root",
                "password": "your_password",
                "database": "your_database"
            }
        }

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
            self._load_configs()
        except Exception as e:
            logger.error(f"[Config] 保存失败：{e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except: pass

    # --- 对外接口 ---

    @classmethod
    def get_config(cls, section: str = None, key: Any=None) -> Any:
        """
        获取配置
        :param section: 配置节名称 (如 'ocr', 'email')，None 表示获取全部
        :param key: 具体的键名，若提供 section 则获取该节下的键
        :return: 配置值或字典
        """

        instance = cls()
        data = instance._configs.copy()

        if section:
            return data.get(section, {}) if not key else data.get(section, {}).get(key)
        return data

    @classmethod
    def set_config(cls, section: str, config_data: Dict[str, Any]):
        """
        更新某一节的配置
        :param section: 配置节名称 (如 'ocr', 'email')
        :param config_data: 包含键值对的字典
        """
        instance = cls()
        if section not in instance._configs:
            instance._configs[section] = {}
        instance._configs[section].update(config_data)
        instance._save_configs()

    @classmethod
    def set_all_config(cls, config_data: Dict[str, Any]):
        """
        保存 config 所有配置。
        :param config_data: 配置字典
        """
        instance = cls()
        instance._configs.update(config_data) # 使用 update 允许部分更新
        instance._save_configs()