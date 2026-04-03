# utils/logUtil.py

import logging
import sys
import os
from datetime import datetime
from multiprocessing import Queue

# 定义统一的日志格式
UNIFORM_FORMAT = '[%(name)s][%(levelname)s][%(asctime)s] %(message)s'

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(current_dir)

# ================= 新增：多进程队列处理器 =================
class NonBlockingQueueHandler(logging.Handler):
    """
    专为多进程设计的非阻塞队列日志处理器。
    当队列满时，自动丢弃日志并打印到 stderr，防止子进程阻塞。
    """
    def __init__(self, queue: Queue, device_id: str = None):
        super().__init__()
        self.queue = queue
        self.device_id = device_id
        # 设置格式化器
        self.setFormatter(logging.Formatter(UNIFORM_FORMAT, datefmt='%Y-%m-%d %H:%M:%S'))

    def emit(self, record):
        try:
            msg = self.format(record)
            # 构造统一的消息对象，方便主进程解析
            log_obj = {
                'device_id': self.device_id or getattr(record, 'device_id', 'Unknown'),
                'msg': f"[{record.asctime}]"+record.message,
                'level': record.levelname,
                'name': record.name
            }
            # 非阻塞放入队列
            if not self.queue.full():
                self.queue.put(log_obj, block=False)
            else:
                # 队列满时，降级打印到 stderr 防止阻塞子进程
                sys.stderr.write(f"[Queue Full] Dropping log: {msg}\n")
        except Exception:
            self.handleError(record)

def init_worker_logger_with_queue(device_id: str, log_queue: Queue):
    """
    【子进程专用】初始化日志，绑定队列和设备ID。
    此函数会创建一个独立的 logger 实例，添加队列处理器，且不写文件。
    """
    logger = logging.getLogger(f"{device_id}")

    # 清除可能存在的旧 handler (防止重复添加)
    if logger.handlers:
        logger.handlers.clear()

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(UNIFORM_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

    # 1. 控制台处理器 (始终添加，方便调试)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. 队列处理器 (核心功能：发送日志回主进程)
    queue_handler = NonBlockingQueueHandler(log_queue, device_id=device_id)
    queue_handler.setLevel(logging.INFO)
    logger.addHandler(queue_handler)
    base_path = get_base_path()
    log_dir = os.path.join(base_path, "logs")
    log_file_path = os.path.join(log_dir, "py-auto.log")

    if log_file_path:
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = logging.FileHandler(log_file_path, encoding='utf-8', mode='a')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    logger.propagate = False
    return logger

# ================= 原有代码保持不变 =================

def setup_global_log(write_to_file=True):
    """
    配置全局日志。
    :param write_to_file: 是否添加文件处理器。主进程为 True，子进程为 False。
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 清除现有的 handler，防止重复添加
    if logger.handlers:
        logger.handlers.clear()
    formatter = logging.Formatter(UNIFORM_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
    # format_file = logging.Formatter(UNIFORM_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

    # 2. 添加控制台处理器 (Console Handler) - 始终添加
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    base_path = get_base_path()
    log_dir = os.path.join(base_path, "logs")
    log_file_path = os.path.join(log_dir, "py-auto.log")

    if write_to_file:
        if log_file_path:
            log_dir = os.path.dirname(log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = logging.FileHandler(log_file_path, encoding='utf-8', mode='a')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    logger.propagate = False
    return logger



def get_logger():
    return setup_global_log(write_to_file=True)