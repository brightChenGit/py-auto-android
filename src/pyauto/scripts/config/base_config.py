import pymysql

DB_CONFIG = {
    'host': 'xxxx',
    'port': 3306,
    'user': 'root',
    'password': 'xxx',
    'database': 'xxx',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    # 这里的 autocommit 建议设为 True
    'autocommit': True,
}

class MysqlConfig:
    def __init__(self):
        self.config=DB_CONFIG.copy()
