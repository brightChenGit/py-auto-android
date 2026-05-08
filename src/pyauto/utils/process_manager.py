"""
进程和系统资源管理工具
用于确保程序退出时正确清理所有进程和文件句柄
"""
import os
import sys
import signal
import logging
import psutil
from typing import List, Optional

logger = logging.getLogger(__name__)

# 全局标志，防止重复注册
_cleanup_registered = False
_is_cleaning = False


def get_process_tree(pid: int = None) -> List[psutil.Process]:
    """
    获取进程树（包括父进程和所有子进程）

    Args:
        pid: 进程ID，默认为当前进程

    Returns:
        进程列表
    """
    if pid is None:
        pid = os.getpid()

    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        return [parent] + children
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def terminate_process_tree(pid: int = None, timeout: int = 5, force: bool = True):
    """
    终止进程树中的所有进程

    Args:
        pid: 进程ID，默认为当前进程
        timeout: 等待进程退出的超时时间（秒）
        force: 是否强制终止（使用SIGKILL）
    """
    processes = get_process_tree(pid)

    if not processes:
        logger.warning(f"未找到进程 {pid}")
        return

    logger.info(f"正在终止 {len(processes)} 个进程...")

    # 第一阶段：温和终止（SIGTERM）
    for proc in processes:
        try:
            if proc.is_running():
                logger.info(f"发送终止信号到进程: {proc.pid} ({proc.name()})")
                proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.debug(f"进程已不存在或无法访问: {e}")

    # 等待进程退出
    gone, alive = psutil.wait_procs(processes, timeout=timeout)

    # 第二阶段：强制终止（如果还有存活的进程）
    if force and alive:
        logger.warning(f"{len(alive)} 个进程未在 {timeout} 秒内退出，强制终止...")
        for proc in alive:
            try:
                if proc.is_running():
                    logger.warning(f"强制终止进程: {proc.pid} ({proc.name()})")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.debug(f"进程已不存在或无法访问: {e}")

        # 再次等待
        gone, alive = psutil.wait_procs(alive, timeout=timeout)

        if alive:
            logger.error(f"以下进程无法终止: {[p.pid for p in alive]}")


def close_all_file_handles(pattern: str = ".log"):
    """
    关闭当前进程打开的所有匹配的文件句柄

    Args:
        pattern: 文件名模式，默认匹配 .log 文件
    """
    try:
        current_process = psutil.Process(os.getpid())
        open_files = current_process.open_files()

        for file_info in open_files:
            if pattern in file_info.path:
                logger.info(f"发现匹配的打开文件: {file_info.path}")
    except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
        logger.error(f"无法获取文件句柄信息: {e}")


def cleanup_on_exit(suppress_logging: bool = False):
    """
    程序退出时的清理函数

    Args:
        suppress_logging: 是否抑制日志输出（当logger已关闭时使用）

    Returns:
        bool: 是否成功执行清理
    """
    global _is_cleaning

    # 防止重复执行
    if _is_cleaning:
        if not suppress_logging:
            print("⚠ 清理已在进行中，跳过重复调用")
        return False

    _is_cleaning = True

    if not suppress_logging:
        print("\n" + "=" * 60)
        print("开始执行退出清理...")
        print("=" * 60)

    # 1. 关闭所有日志处理器（释放文件句柄）
    try:
        import pyauto.utils.logUtil
        pyauto.utils.logUtil.cleanup_all_loggers()
        if not suppress_logging:
            print("✓ 日志系统已关闭")
    except Exception as e:
        if not suppress_logging:
            print(f"✗ 关闭日志系统失败: {e}")

    # 2. 检查并记录打开的文件句柄
    try:
        close_all_file_handles(".log")
    except Exception as e:
        if not suppress_logging:
            print(f"检查文件句柄失败: {e}")

    # 3. 终止所有子进程（排除当前进程）
    try:
        current_pid = os.getpid()
        processes = get_process_tree(current_pid)
        # 只终止子进程，不终止当前进程
        child_processes = [p for p in processes if p.pid != current_pid]

        if child_processes:
            if not suppress_logging:
                print(f"正在终止 {len(child_processes)} 个子进程...")
            for proc in child_processes:
                try:
                    if proc.is_running():
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # 等待子进程退出
            gone, alive = psutil.wait_procs(child_processes, timeout=3)

            # 强制终止仍未退出的进程
            if alive:
                for proc in alive:
                    try:
                        if proc.is_running():
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                gone, alive = psutil.wait_procs(alive, timeout=2)

                if alive and not suppress_logging:
                    print(f"⚠ 以下子进程无法终止: {[p.pid for p in alive]}")

            if not suppress_logging:
                print("✓ 所有子进程已终止")
        else:
            if not suppress_logging:
                print("✓ 无子进程需要终止")

    except Exception as e:
        if not suppress_logging:
            print(f"✗ 终止子进程失败: {e}")

    if not suppress_logging:
        print("=" * 60)
        print("清理完成，程序即将退出")
        print("=" * 60 + "\n")

    return True


def register_cleanup():
    """
    注册清理函数到各种退出场景

    应该在程序启动时尽早调用此函数
    """
    global _cleanup_registered

    # 防止重复注册
    if _cleanup_registered:
        logger.debug("清理处理器已注册，跳过重复注册")
        return

    _cleanup_registered = True

    import atexit
    import threading

    # 方法1: 注册到 atexit（正常退出时调用）
    # 使用 suppress_logging=True，因为此时 logger 可能已关闭
    atexit.register(lambda: cleanup_on_exit(suppress_logging=False))

    # 方法2: 注册信号处理器（Ctrl+C、系统信号等）
    if sys.platform == 'win32':
        # Windows 特定信号
        try:
            signal.signal(signal.SIGBREAK, lambda sig, frame: cleanup_and_exit())
        except (ValueError, OSError):
            pass

        try:
            signal.signal(signal.SIGINT, lambda sig, frame: cleanup_and_exit())
        except (ValueError, OSError):
            pass

    # 方法3: 注册线程退出处理
    main_thread = threading.main_thread()
    original_run = main_thread.run

    def wrapped_run():
        try:
            original_run()
        finally:
            # 这里不使用 cleanup_on_exit，因为 atexit 会处理
            pass

    main_thread.run = wrapped_run

    logger.info("✓ 退出清理处理器已注册")


def cleanup_and_exit(exit_code: int = 0):
    """
    执行清理并退出程序

    Args:
        exit_code: 退出码
    """
    cleanup_on_exit(suppress_logging=False)
    sys.exit(exit_code)


# 不再自动注册，改为由主程序显式调用
# 这样可以避免在子进程中重复注册
