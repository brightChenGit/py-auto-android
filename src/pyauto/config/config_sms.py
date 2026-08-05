# 文件名：config_sms.py
import os
import sys
import json
import time
import threading
import sqlite3
from typing import Dict, Any, List, Optional
from pyauto.config.config_base import UnifiedConfigManager
from pyauto.utils.mail_utils import send_email_notification
import pyauto.utils.logUtil

logger = pyauto.utils.logUtil.get_logger()

def get_config_root():
    """获取配置文件的根目录。兼容开发环境和打包后的 EXE 环境。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SmsConfigManager:
    """
    基于 SQLite 的配置与验证码管理器。
    线程安全，使用 WAL 模式支持高并发读写。
    """
    _base_dir = get_config_root()
    # 数据库文件将和原来的 JSON 文件在同一目录下
    DB_FILE_PATH = os.path.join(_base_dir, "config", "sms_configs.db")

    _instance = None
    _instance_lock = threading.Lock() # 用于保护单例实例的创建
    _db_lock = threading.RLock()      # 用于保护数据库连接和操作的锁

    def __new__(cls):
        # 双重检查锁实现单例
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super(SmsConfigManager, cls).__new__(cls)
                    cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        """初始化数据库连接和表结构"""
        config_dir = os.path.dirname(self.DB_FILE_PATH)
        if config_dir and not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
            except OSError as e:
                logger.error(f"[Config] 无法创建配置目录：{e}")
                return

        try:
            # 连接到 SQLite 数据库
            self.conn = sqlite3.connect(self.DB_FILE_PATH, check_same_thread=False)
            self.conn.execute('PRAGMA journal_mode = WAL;')
            cursor = self.conn.cursor()

            # 1. 创建通用配置表
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS general_configs (
                                                                          key TEXT PRIMARY KEY,
                                                                          value TEXT NOT NULL
                           )
                           ''')

            # 2. 创建验证码表 (修改 timestamp 字段类型为 DATETIME)
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS verification_codes (
                                                                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                             phone_number TEXT NOT NULL,
                                                                             app_name TEXT NOT NULL,
                                                                             code TEXT NOT NULL,
                                                                             content TEXT NOT NULL,
                                                                             timestamp DATETIME NOT NULL,
                                                                             is_used INTEGER NOT NULL DEFAULT 0
                           )
                           ''')

            # 3. 为验证码表创建独立的索引
            cursor.execute('''
                           CREATE INDEX IF NOT EXISTS idx_phone_app ON verification_codes (phone_number, app_name)
                           ''')
            cursor.execute('''
                           CREATE INDEX IF NOT EXISTS idx_timestamp ON verification_codes (timestamp)
                           ''')

            self.conn.commit()
            logger.info("[Config] 数据库初始化成功")
        except Exception as e:
            logger.error(f"[Config] 数据库初始化失败: {e}")

    # ==========================================
    # 通用配置操作接口
    # ==========================================
    @classmethod
    def get_config(cls, key: str) -> Any:
        """获取通用配置"""
        instance = cls()
        with cls._db_lock:
            try:
                cursor = instance.conn.execute("SELECT value FROM general_configs WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
            except Exception as e:
                logger.error(f"[Config] 获取配置失败: {e}")
                return None

    @classmethod
    def save_config(cls, key: str, data: Any):
        """保存通用配置"""
        instance = cls()
        data_json = json.dumps(data, ensure_ascii=False)
        with cls._db_lock:
            try:
                instance.conn.execute(
                    "INSERT OR REPLACE INTO general_configs (key, value) VALUES (?, ?)",
                    (key, data_json)
                )
                instance.conn.commit()
            except Exception as e:
                logger.error(f"[Config] 保存配置失败: {e}")

    # ==========================================
    # 验证码专用业务逻辑
    # ==========================================
    @classmethod
    def save_verification_code(cls, phone_number: str, app_name: str, content: str, code: str):
        """保存接收到的验证码短信"""
        instance = cls()
        phone_number = str(phone_number).strip()

        with cls._db_lock:
            try:
                # 使用 datetime('now', 'localtime') 直接在 SQL 中生成当前本地时间
                instance.conn.execute(
                    '''INSERT INTO verification_codes (phone_number, app_name, code, content, timestamp, is_used)
                       VALUES (?, ?, ?, ?, datetime('now', 'localtime'), 0)''',
                    (phone_number, app_name, code, content)
                )
                instance.conn.commit()

                # 可选：限制每个应用只保留最近 N 条，防止数据库过大
                # 这里使用窗口函数删除多余的旧记录
                instance.conn.execute(
                    '''DELETE FROM verification_codes
                       WHERE id NOT IN (
                           SELECT id FROM (
                                              SELECT id, ROW_NUMBER() OVER (PARTITION BY phone_number, app_name ORDER BY timestamp DESC) as rn
                                              FROM verification_codes
                                              WHERE phone_number = ? AND app_name = ?
                                          ) WHERE rn <= 10
                       ) AND phone_number = ? AND app_name = ?''',
                    (phone_number, app_name, phone_number, app_name)
                )
                instance.conn.commit()

                # 发送邮件通知
                emailConfig = UnifiedConfigManager.get_config("email")
                if emailConfig and emailConfig.get("task_captcha"):
                    send_email_notification("[验证码通知]", f"收到手机号{phone_number}：\n{str(content)}")
            except Exception as e:
                logger.error(f"[Config] 保存验证码失败: {e}")

    @classmethod
    def get_latest_unused_code(cls, phone_number: str, app_name: str) -> Optional[str]:
        """
        获取最新的一条未使用的验证码（5分钟内有效），并自动标记为已使用
        :return: 验证码字符串或 None
        """
        instance = cls()
        phone_number = str(phone_number).strip()

        with cls._db_lock:
            try:
                # 使用 datetime('now', '-5 minutes', 'localtime') 在 SQL 中计算5分钟前的时间
                cursor = instance.conn.execute(
                    '''SELECT id, code FROM verification_codes
                       WHERE phone_number = ? AND app_name = ? AND is_used = 0
                         AND timestamp > datetime('now', '-5 minutes', 'localtime')
                       ORDER BY timestamp DESC LIMIT 1''',
                    (phone_number, app_name)
                )
                row = cursor.fetchone()

                if row:
                    code_id, code = row
                    # 2. 标记为已使用
                    instance.conn.execute(
                        "UPDATE verification_codes SET is_used = 1 WHERE id = ?",
                        (code_id,)
                    )
                    instance.conn.commit()
                    return code
                return None
            except Exception as e:
                logger.error(f"[Config] 获取验证码失败: {e}")
                return None

    @classmethod
    def get_latest_unused_code_info(cls, phone_number: str, app_name: str) -> Optional[Dict]:
        """
        获取最新的一条未使用的验证码详细信息（不标记为已使用）
        :return: 字典或 None
        """
        instance = cls()
        phone_number = str(phone_number).strip()
        with cls._db_lock:
            try:
                cursor = instance.conn.execute(
                    '''SELECT code, content, timestamp, is_used FROM verification_codes
                       WHERE phone_number = ? AND app_name = ? AND is_used = 0
                       ORDER BY timestamp DESC LIMIT 1''',
                    (phone_number, app_name)
                )
                row = cursor.fetchone()
                if row:
                    # 直接返回从数据库取出的时间字符串
                    return {
                        "code": row[0],
                        "content": row[1],
                        "timestamp": row[2], # 这已经是 'YYYY-MM-DD HH:MM:SS' 格式的字符串
                        "is_used": bool(row[3])
                    }
                return None
            except Exception as e:
                logger.error(f"[Config] 获取验证码信息失败: {e}")
                return None