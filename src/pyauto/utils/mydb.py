import os

# 数据库配置
import pymysql
import logging
from typing import Dict, Any, Optional, List
from dbutils.pooled_db import PooledDB # 或者使用 PersistentDB

DB_CONFIG = {
    'host': 'xxxx',
    'port': 3306,
    'user': 'root',
    'password': 'xxxx',
    'database': 'xxxx',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    # 这里的 autocommit 建议设为 True
    'autocommit': True,
}

class DBHelper:
    def __init__(self, config: Dict[str, Any] = None, logger: Optional[logging.Logger] = None):
        self.config = config or DB_CONFIG.copy()
        self.logger = logger or logging.getLogger(__name__)

        # 初始化连接池/持久连接
        # maxconnections=1 表示每个线程/进程只持有一个连接（最省资源且安全）
        # 在多进程中，每个进程都会初始化自己的 pool 实例
        pool_size = self.config.pop('maxconnections', 1)

        self.pool = PooledDB(
            creator=pymysql,
            maxconnections=pool_size, # 动态值
            mincached=pool_size,
            blocking=True,
            ping=1,
            **self.config
        )

    @property
    def connection(self):
        # 从池中获取连接，DBUtils 会自动处理 ping 和重连
        return self.pool.connection()

    def _execute(self, sql: str, params=None, commit=False) -> Any:
        # 使用 with 语句自动管理游标关闭，连接由 pool 管理
        try:
            conn = self.connection
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if commit:
                    conn.commit()
                    return cur.rowcount
                return cur.fetchall()
        except Exception as e:
            self.logger.error(f"数据库执行错误: {e}")
            raise

    def query(self, sql: str, params=None) -> List[Dict]:
        """查询多行"""
        return self._execute(sql, params, commit=False)

    def query_one(self, sql: str, params=None) -> Optional[Dict]:
        """查询单行"""
        result = self._execute(sql, params, commit=False)
        return result[0] if result else None

    def execute(self, sql: str, params=None) -> int:
        """执行 INSERT/UPDATE/DELETE，返回影响行数"""
        return self._execute(sql, params, commit=True)

    def execute_many(self, sql: str, params_list) -> int:
        """
        批量执行 SQL
        :param params_list: 列表的元组 或 列表的列表
        """
        try:
            with self.connection.cursor() as cur:
                cur.executemany(sql, params_list)
                self.connection.commit()
                return cur.rowcount
        except (pymysql.err.OperationalError, pymysql.err.InterfaceError) as e:
            self.logger.warning(f"批量执行异常 {e}，尝试重连...")
            self._reconnect()
            # 重试
            with self.connection.cursor() as cur:
                cur.executemany(sql, params_list)
                self.connection.commit()
                return cur.rowcount

    def close(self):
        """关闭当前进程连接"""
        if hasattr(self, 'pool') and self.pool:
            self.pool.close()
            self.logger.info(f"进程 [{os.getpid()}] 连接池已关闭")


    # === 上下文管理器支持 ===
    def __enter__(self):
        # 每次进入都确保连接可用
        if not self.connection or not self.connection.open:
            self._reconnect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 通常在进程退出时调用
        self.close()


    def _reconnect(self):
        """重建数据库连接池"""
        try:
            old_pool = getattr(self, 'pool', None)
            if old_pool:
                try:
                    old_pool.close()
                    self.logger.debug("旧连接池已关闭")
                except:
                    pass # 忽略关闭时的异常

            # 重新创建
            self.pool = PooledDB(
                creator=pymysql,
                maxconnections=self.config.get('maxconnections', 1),
                mincached=self.config.get('mincached', 1),
                blocking=self.config.get('blocking', True),
                ping=self.config.get('ping', 1),
                **self.config
            )
            self.logger.info("数据库连接重建成功")
        except Exception as e:
            self.logger.error(f"重建连接失败: {e}")
            raise