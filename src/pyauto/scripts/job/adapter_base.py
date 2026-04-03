import logging
import time
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Union
from datetime import datetime
import uiautomator2 as u2

import pyauto.utils.logUtil


# 获取全局 logger 实例
class BaseAdapter(ABC):
    """
    基础适配器 (BaseAdapter) - Python 版本
    注意：此类作为基类，定义了接口规范。具体 App 的适配器需继承此类并实现具体方法。
    """

    def __init__(self, app_name: str, package_name: str, driver: Optional[u2.Device] = None,logger: Optional[logging.Logger] = None):
        """
        初始化适配器
        :param app_name: 应用名称 (对应 JS 中的 appName)
        :param driver: uiautomator2 设备实例 (可选，若不提供需在子类中自行连接)
        """
        self.app_name = app_name
        self.package_name = package_name
        self.driver = driver if driver else u2.connect()
        # 设置全局默认等待时间为 10 秒
        self.driver.settings['wait_timeout'] = 5
        # 点击 (click)、长按 (long_click) 和 滑动 (swipe) 等交互动作执行后的等待时间
        self.driver.settings['operation_delay'] = (0.1, 0.5) # 操作后随机延迟 0.2~0.5 秒，防止手速过快被防爬

        self.root_node = None  # 对应 JS 中的 this.rootNode，模拟当前屏幕根节点

        # 初始化日志器，带上 App 名称前缀
        self.logger = logger
        self.logger.info(f"BaseAdapter 初始化完成: {app_name}")


    @abstractmethod
    def swipe_up(self, first_search: bool) -> None:
        """
        UI: 上滑翻页
        对应 JS: BaseAdapter.prototype.swipeUp
        :param first_search: 是否为首次搜索 (可能影响滑动策略)
        """
        pass

    # ================= 默认实现方法 (对应 JS 中有具体实现的 goBack) =================

    def go_back(self) -> None:
        """
        UI: 返回上一页
        默认实现：执行 back() 操作
        对应 JS: BaseAdapter.prototype.goBack
        """
        self.logger.info("执行返回操作 (goBack)")
        self.driver.press("back")
        time.sleep(1.5)  # 对应 JS sleep(1500)

    # ================= 工具方法 (对应 JS 中的 log) =================

    def info(self, msg: str) -> None:
        """
        日志输出
        对应 JS: BaseAdapter.prototype.log
        :param msg: 日志消息
        """
        # JS 原逻辑: var time = new Date().toLocaleTimeString();
        # Python logging 默认已包含时间戳，这里直接格式化消息
        log_msg = f"[{self.app_name}] {msg}"
        self.logger.info(log_msg)

        # 注：JS 注释中提到的 Vue 钩子在纯 Python 后端环境中通常不需要，
        # 如需对接前端展示，可在此处添加回调或写入共享队列。
    def warn(self, msg: str) -> None:
        """
        日志输出
        对应 JS: BaseAdapter.prototype.log
        :param msg: 日志消息
        """
        # JS 原逻辑: var time = new Date().toLocaleTimeString();
        # Python logging 默认已包含时间戳，这里直接格式化消息
        log_msg = f"[{self.app_name}] {msg}"
        self.logger.warn(log_msg)

        # 注：JS 注释中提到的 Vue 钩子在纯 Python 后端环境中通常不需要，
        # 如需对接前端展示，可在此处添加回调或写入共享队列。
    def error(self, msg: str) -> None:
        """
        日志输出
        对应 JS: BaseAdapter.prototype.log
        :param msg: 日志消息
        """
        # JS 原逻辑: var time = new Date().toLocaleTimeString();
        # Python logging 默认已包含时间戳，这里直接格式化消息
        log_msg = f"[{self.app_name}] {msg}"
        self.logger.error(log_msg)

        # 注：JS 注释中提到的 Vue 钩子在纯 Python 后端环境中通常不需要，
        # 如需对接前端展示，可在此处添加回调或写入共享队列。
    def _get_ocr_text_in_area(self, bounds: List[int]) -> List[str]:
        """在指定区域进行 OCR"""
        try:
            img = self.d.screenshot()
            # 调用工具类
            return self.ocr.ocr_crop(img, bounds)
        except Exception as e:
            self.error(f"区域 OCR 失败: {e}")
            return []

    def _get_screen_texts_ocr(self) -> List[str]:
        """全屏 OCR"""
        w, h = self.d.window_size()
        return self._get_ocr_text_in_area([0, 0, w, h])

    def _ocr_click(self, text: str) -> bool:
        """OCR 识别并点击"""
        try:
            screenshot = self.d.screenshot()
            result = self.ocr.ocr_full_screen(screenshot)
            if result and result[0]:
                for line in result[0]:
                    content = line[1][0]
                    if text in content:
                        coords = line[0]
                        x = int((coords[0][0] + coords[2][0]) / 2)
                        y = int((coords[0][1] + coords[2][1]) / 2)
                        self.d.click(x, y)
                        self.info(f"OCR 点击成功: {content}")
                        return True
            return False
        except Exception as e:
            self.error(f"OCR 点击异常: {e}")
            return False

    # ================= 辅助方法 (Python 特有增强，非 JS 原版但推荐使用) =================

    def wait(self, seconds: float = 1.0) -> None:
        """简化等待调用"""
        time.sleep(seconds)

    def get_current_time(self) -> str:
        """获取当前时间字符串，模拟 JS new Date().toLocaleTimeString()"""
        return datetime.now().strftime("%H:%M:%S")

    def click_search(self,selector):
        #解决search失效情况下，使用输入法的搜索按钮
        selector.click()
        keyboard=self.driver(resourceId="com.github.uiautomator:id/keyboard")
        if not keyboard.wait(timeout=5):
            self.error("输入法不存在")
        # self.error(f"{keyboard.info}")
        bounds = keyboard.info['bounds']
        w = bounds['right']
        h = bounds['bottom']
        # 计算坐标
        click_x = int(w * 0.60)
        click_y = int(h * 0.97)
        self.driver.click(click_x,click_y)


