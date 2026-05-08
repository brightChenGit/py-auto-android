import json
import os
import sys
import pymysql
import importlib

class MysqlConfigManager:
    def __init__(self):
        # 内置的默认配置 (Fallback)
        self._default_config = {
            'host': 'xxxx',
            'port': 3306,
            'user': 'root',
            'password': 'xxxx',
            'database': 'xxxx',
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': True,
        }
        self.config = self._load_config()

    def _get_base_path(self):
        """
        获取程序运行的基础路径。
        如果是 PyInstaller 打包后的 exe，使用 _MEIPASS；
        如果是普通脚本运行，使用当前文件所在目录。
        """
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            return os.path.dirname(sys.executable)
        else:
            # 开发环境
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _load_config(self):
        """加载配置：先尝试读取文件，失败则使用默认配置"""
        _config_dir=os.path.join(self._get_base_path(), "config")
        config_path = os.path.join(_config_dir, 'sql.json')
        print(f"[INFO] 从 {config_path} 加载配置")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    cursor_class_str = file_config.get('cursorclass')
                    if isinstance(cursor_class_str, str):
                        try:
                            # 动态导入模块和类
                            # 例如: "pymysql.cursors.DictCursor" -> 导入 pymysql.cursors 模块，获取 DictCursor 类
                            module_path, class_name = cursor_class_str.rsplit('.', 1)
                            module = importlib.import_module(module_path)
                            file_config['cursorclass'] = getattr(module, class_name)
                            # print(f"[INFO] ✅ 成功将 cursorclass 转换为类: {class_name}")
                        except Exception as e:
                            print(f"[ERROR] ❌ cursorclass 转换失败: {e}，将使用默认游标")
                            file_config['cursorclass'] = None

                    print(f"[INFO] 成功从 {config_path} 加载配置")
                    return file_config
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARN] 读取配置文件失败: {e}，将使用默认内置配置")

        # 文件不存在或读取失败，使用默认配置
        print("[INFO] 未找到 sql.json，使用内置默认配置")
        return self._default_config.copy()

    def get_db_config(self):
        """返回数据库配置字典"""
        return self.config.copy()

# 全局单例实例
mysqlConfig = MysqlConfigManager()