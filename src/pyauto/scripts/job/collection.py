import time
import logging
from typing import List, Dict, Optional, Any

# 假设这些模块已存在
from pyauto.utils.mydb import DBHelper

from pyauto.scripts.job.adapter_xdt import XdtAdapter
from pyauto.scripts.job.adapter_base import BaseAdapter
import uiautomator2 as u2
from pyauto.utils.mydb import DBHelper
from pyauto.scripts.dao.mysql_dao import SqlByStationDAO # 导入模型
from pyauto.scripts.config.base_config import MysqlConfig # 导入模型


class CollectionController:

    def __init__(self, device_id: str = None,config: Dict[str, Any]=None,logger: Optional[logging.Logger] = None,driver: Optional[u2.Device] = None):

        self.adapters: List[BaseAdapter] = []
        self.logger=logger
        self.config=config
        self.d = driver if driver else u2.connect(device_id)
        self.db = DBHelper(config=MysqlConfig().config,logger=self.logger) # 初始化数据库 helper
        self.sql = SqlByStationDAO(self.db)



    def run(self):
        """主入口"""
        try:
            self.logger.info("=== 采集脚本启动 ===")

        except Exception as e:
            self.logger.error(f"全局异常: {e}", exc_info=True)
        finally:
            self.logger.info("=== 脚本结束 ===")

# if __name__ == "__main__":
#     controller = MainController(null)
#     controller.run()