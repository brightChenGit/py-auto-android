"""
mysql_dao.py
业务模型层 - 优化版
使用装饰器模式统一处理数据库操作的日志记录和异常捕获。
"""
import functools
import logging
from typing import List, Dict, Callable
from datetime import datetime
from pyauto.utils.mydb import DBHelper

# --- 1. 核心装饰器定义 ---
def db_operation_logger(success_msg: str, error_msg: str, default_return=None):
    """
    数据库操作通用装饰器
    :param success_msg: 成功时的日志描述
    :param error_msg: 错误时的日志描述
    :param default_return: 发生异常时的默认返回值
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 策略：尝试从 kwargs 获取 db，如果找不到，则尝试从 args[0] (即 self) 获取
            db = kwargs.get('db')
            if not db and args:
                db = getattr(args[0], 'db', None)

            if not db:
                # 如果连数据库连接都找不到，记录错误并返回默认值
                logging.getLogger(__name__).error(f"执行 {func.__name__} 时未找到数据库连接实例")
                return default_return

            try:
                result = func(*args, **kwargs)

                # 智能日志记录
                if isinstance(result, int):
                    db.logger.info(f"{success_msg}，影响行数: {result}")
                elif isinstance(result, list):
                    db.logger.info(f"{success_msg}，查询条数: {len(result)}")
                else:
                    db.logger.info(success_msg)

                return result
            except Exception as e:
                db.logger.error(f"{error_msg}: {e}")
                return default_return
        return wrapper
    return decorator



# --- 3. 站点业务数据访问对象 ---
class SqlByStationDAO:
    def __init__(self, db: DBHelper):
        self.db = db

    @db_operation_logger(
        success_msg="查询xx配置列表",
        error_msg="查询xx配置失败",
        default_return=[]
    )
    def get_list_config(self, app_name: str) -> List[Dict]:
        sql = "SELECT * FROM xx WHERE xx=%s AND xx=%s ORDER BY xxx"
        # 直接返回查询结果，异常由装饰器捕获
        return self.db.query(sql, ("未完成", app_name))

    @db_operation_logger(
        success_msg="批量插入xx成功",
        error_msg="批量插入xx失败",
        default_return=0
    )
    def insert_xxx_multi(self, rows: List[Dict]) -> int:
        if not rows:
            return 0

        sql = """ INSERT INTO xxx
                  (`xxx`, `xxx`, `xx`)
                  VALUES (%s, %s, %s) """

        values = [(
            row.get("xxx"), row.get("xxx"), row.get("xxx")
         ) for row in rows]

        return self.db.execute_many(sql, values)

    @db_operation_logger(
        success_msg="更新xx配置状态成功",
        error_msg="更新xx配置状态失败",
        default_return=0
    )
    def update_xxx_id(self, data_1: str, data_2: str, status: str) -> int:
        sql = "UPDATE xxx SET xxx=%s WHERE xxx=%s AND xx=%s"
        return self.db.execute(sql, (data_1, data_2, status))

    @db_operation_logger(
        success_msg="删除xx数据成功",
        error_msg="删除xxx数据失败",
        default_return=0
    )
    def delete_by_station_near_by_id(self, data_1: str, data_2: str) -> int:
        sql = "DELETE FROM xxx WHERE xx=%s AND xx=%s"
        return self.db.execute(sql, (data_1, data_2))

