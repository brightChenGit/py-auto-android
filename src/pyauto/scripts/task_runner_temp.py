# scripts/task_runner.py
import datetime
import sys
import time
import logging
from multiprocessing import Event
from typing import Dict, Any
import uiautomator2 as u2
from pyauto.scripts.job.collection import CollectionController
#task_runner.py 备份

def run_business_logic(device_id: str, config: Dict[str, Any], stop_event: Event, logger: logging.Logger):
    """
    子进程任务入口函数。
    此函数必须是顶层函数，以便 ProcessPoolExecutor 能够序列化并调用它。
    
    :param device_id: 设备标识
    :param config: 任务配置字典
    :param stop_event: 多进程停止信号事件
    :param logger: 专用日志器 (输出会自动路由到主进程 Queue)
    """
    logger.info(f"=== 任务开始 (Device: {device_id}) ===")
    # u2.connect(device_id) 安装atx，后续调用放在后面使用
    # u2.connect_usb(device_id)
    d = u2.connect(device_id)

    # 触发自动安装atx+输入法
    try:
        d._setup_ime()
        d._setup_jar()
    except Exception as e:
        logging.info(f"初始化失败: {e}")
    # d.set_fastinput_ime(False)
    CollectionController(device_id,config,logger).run()
    count = 0
    while not stop_event.is_set():
        # 【关键】先检查停止信号，再做事
        if stop_event.is_set():
            logger.warning(">>> 检测到停止信号，退出循环")
            break

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count += 1
        msg = f"心跳检测 #{count} - 时间: {now}"

        logger.info(msg)
        if stop_event.is_set():
            return
        time.sleep(1)


    # 清理资源
    _cleanup_resources(device_id, logger)


def _cleanup_resources(device_id: str, logger: logging.Logger):
    """
    任务被强制停止时的清理逻辑。
    例如：关闭应用、释放端口、删除临时文件等。
    """
    logger.info(f"正在清理设备 {device_id} 的资源...")
    time.sleep(0.5) # 模拟清理时间
    logger.info("资源清理完成。")