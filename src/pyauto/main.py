# 文件名: main.py
from pyauto.page.app_page import run_main_app
import multiprocessing
import threading
import traceback
import sys
import time
from pyauto.utils.process_manager import register_cleanup

# 1. 导入两个独立服务的启动函数
from pyauto.web.sms_service import start_sms_server
from pyauto.web.ocr_service import start_ocr_server

def start_service_process(service_name, target_func, stop_event):
    """
    通用的服务进程包装函数。
    :param service_name: 服务名称，用于日志标识
    :param target_func: 服务的启动函数，如 start_sms_server
    :param stop_event: 用于进程间通信的停止事件
    """
    print(f"[MAIN] 正在启动 {service_name} 进程...", flush=True)
    try:
        target_func()
    except Exception as e:
        print(f"[MAIN] {service_name} 进程意外退出: {e}", flush=True)
        traceback.print_exc()

def monitor_services(sms_proc, ocr_proc, stop_event):
    """
    在独立线程中运行的监控函数，负责检查两个服务进程的状态并实现自动重启。
    """
    print("[MAIN] 后台线程：开始监控所有服务进程...", flush=True)
    while not stop_event.is_set():
        # --- 监控 SMS 服务 ---
        if not sms_proc.is_alive():
            if not stop_event.is_set():
                print("[MAIN] 检测到 SMS 服务进程已退出，正在尝试重启...", flush=True)
                # 重新创建并启动进程
                sms_proc = multiprocessing.Process(
                    target=start_service_process,
                    args=("SMS-SERVICE", start_sms_server, stop_event),
                    daemon=True
                )
                sms_proc.start()
                print(f"[MAIN] SMS 服务进程已重启，新 PID: {sms_proc.pid}", flush=True)

        # --- 监控 OCR 服务 ---
        if not ocr_proc.is_alive():
            if not stop_event.is_set():
                print("[MAIN] 检测到 OCR 服务进程已退出，正在尝试重启...", flush=True)
                # 重新创建并启动进程
                ocr_proc = multiprocessing.Process(
                    target=start_service_process,
                    args=("OCR-SERVICE", start_ocr_server, stop_event),
                    daemon=True
                )
                ocr_proc.start()
                print(f"[MAIN] OCR 服务进程已重启，新 PID: {ocr_proc.pid}", flush=True)

        time.sleep(1)


def main_logic():
    multiprocessing.freeze_support()

    # 1. 创建停止事件，用于进程间通信
    # manager = multiprocessing.Manager()
    # stop_event = manager.Event()
    stop_event = multiprocessing.Event()

    # 2. 启动 SMS 服务进程
    sms_process = multiprocessing.Process(
        target=start_service_process,
        args=("SMS-SERVICE", start_sms_server, stop_event),
        daemon=True
    )
    sms_process.start()
    print(f"[MAIN] SMS 服务进程已启动，PID: {sms_process.pid}", flush=True)

    # 3. 启动 OCR 服务进程
    ocr_process = multiprocessing.Process(
        target=start_service_process,
        args=("OCR-SERVICE", start_ocr_server, stop_event),
        daemon=True
    )
    ocr_process.start()
    print(f"[MAIN] OCR 服务进程已启动，PID: {ocr_process.pid}", flush=True)

    # 4. 启动后台监控线程
    monitor_thread = threading.Thread(
        target=monitor_services,
        args=(sms_process, ocr_process, stop_event),
        daemon=True
    )
    monitor_thread.start()

    # 5. 启动主 GUI 界面（主线程继续执行）
    try:
        print("[MAIN] 启动 py-auto 主界面...", flush=True)
        register_cleanup()
        run_main_app()
    except Exception as e:
        print(f"[MAIN] 启动失败：{e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 6. 当主程序 (GUI) 退出时，强制终止所有子进程
        print("[MAIN] 主程序即将退出，正在终止所有服务进程...", flush=True)
        stop_event.set()

        for proc in [sms_process, ocr_process]:
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=5)
                if proc.is_alive():
                    proc.kill()
        sys.exit(0)


if __name__ == "__main__":
    main_logic()