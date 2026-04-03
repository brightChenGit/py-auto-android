# main.py
from pyauto.page.app_page import run_main_app
import multiprocessing

if __name__ == "__main__":
    # 1. 在开发环境(__name__ == "__main__")：通常无副作用，直接跳过。
    # 2. 在打包后的子进程环境：识别出这是子进程启动，拦截后续代码，
    #    转而执行多进程任务的目标函数，防止重复启动 GUI 界面。
    multiprocessing.freeze_support()
    # 直接启动主界面
    # 不再有 "子任务模式" 的判断，因为子任务是由另一个独立的 python.exe 进程运行的
    print("[MAIN] 启动 py-auto 主界面...", flush=True)
    try:
        run_main_app()
    except Exception as e:
        print(f"[MAIN] 启动失败：{e}", flush=True)
        import traceback
        traceback.print_exc()


