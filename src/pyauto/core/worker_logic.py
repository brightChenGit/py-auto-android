import asyncio
import sys
import os
import logging
from typing import Dict, Any
from multiprocessing import Queue
import multiprocessing as mp

#
import pyauto.utils.logUtil
from pyauto.utils import logUtil

# 全局 logger 用于子进程本地 fallback
local_logger = pyauto.utils.logUtil.get_logger()

def get_project_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(current_dir)

class WorkerLogicAsync:
    def __init__(self, device_id: str, log_queue: Queue, cmd_queue: Queue = None, logger=None):
        self.device_id = device_id
        self.log_queue = log_queue
        self.cmd_queue = cmd_queue
        # ✅ 修复 1: 使用 multiprocessing.Event，它是线程安全且进程安全的
        self.stop_event = mp.Event()
        self._is_running = False
        self.logger = logger if logger else pyauto.utils.logUtil.get_logger()

    def _send_log(self, msg: str, level: str = "INFO"):
        """发送日志到主进程队列 (带超时保护)"""
        try:
            # ✅ 修复 2: 使用 put_nowait 或带超时的 put，防止卡死
            if not self.log_queue.full():
                self.log_queue.put({'device_id': self.device_id, 'msg': msg, 'level': level}, block=False)
            else:
                # 队列满了，降级打印到 stderr，不要阻塞主线程
                print(f"[{self.device_id}] Log queue full, dropping: {msg}", file=sys.stderr)
        except Exception as e:
            print(f"[{self.device_id}] Log queue error: {e}", file=sys.stderr)

    async def start_task(self, config: Dict[str, Any]) -> bool:
        self._send_log("开始执行采集任务...", "SYS")
        try:
            loop = asyncio.get_running_loop()
            self.logger.critical("⚙️⚙️⚙️ [START_TASK] 准备提交到线程池... ⚙️⚙️⚙️")
            def business_wrapper():
                # 这里的 local_logger 需要确保也能处理停止信号，或者直接传 stop_event 给 run_business_logic
                # 假设 task_runner.py 已经修改为接受 mp.Event
                from pyauto.scripts.task_runner import run_business_logic
                run_business_logic(self.device_id, config, self.stop_event, self.logger)

            # 在线程池运行
            # ⚠️ 注意：即使这里用了线程池，如果 run_business_logic 内部不检查 stop_event，它依然停不下来
            # 必须确保 task_runner.py 内部有 while True: if stop_event.is_set(): break
            await loop.run_in_executor(None, business_wrapper)
            self.logger.critical("⚙️⚙️⚙️ [START_TASK] 线程池任务返回了！ ⚙️⚙️⚙️")
            if not self.stop_event.is_set():
                self._send_log("任务执行成功", "SYS")
            else:
                self._send_log("任务已被用户停止", "SYS")
            return True

        except Exception as e:
            # ... (异常处理保持不变)
            self.logger.error(f"业务逻辑执行出错：{e}", exc_info=True)
            print(f"{e}")
            return False
        finally:
            self._is_running = False


    async def monitor_loop(self):
        # 【关键调试】一进来就打印，证明协程开始执行了
        print("!!! MONITOR_LOOP ENTERED !!!")
        self.logger.info("👀 [Monitor] 监控循环协程已启动")

        try:
            count = 0
            while self._is_running:
                # count += 1
                # # 每次循环都打印，看它到底跑没跑
                # if count <= 5 or count % 10 == 0:
                #     print(f"!!! MONITOR_LOOP HEARTBEAT #{count} !!!")
                #     self.logger.debug(f"👀 [Monitor] 心跳 #{count}, 队列大小: {self.cmd_queue.qsize() if self.cmd_queue else 'None'}")

                # 检查队列
                if self.cmd_queue and not self.cmd_queue.empty():
                    try:
                        cmd = self.cmd_queue.get_nowait()
                        print(f"!!! RECEIVED CMD: {cmd} !!!")
                        self.logger.critical(f"⚡️ [Monitor] 收到指令: {cmd}")

                        if cmd.get('action') == 'stop':
                            self.logger.critical("⚡️⚡️⚡️ 设置 stop_event ⚡️⚡️⚡️")
                            self.stop_event.set()
                            break
                    except Exception as e:
                        self.logger.error(f"取命令出错: {e}")

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            self.logger.warning("⚠️ [Monitor] 被取消")
        except Exception as e:
            self.logger.error(f"💥 [Monitor] 崩溃: {e}")
        finally:
            print("!!! MONITOR_LOOP EXITED !!!")
            self.logger.info("👋 [Monitor] 监控循环已退出")

    async def stop_task(self):
        """接收停止指令"""
        if not self._is_running:
            return
        self._send_log("收到停止指令", "WARN")
        self.stop_event.set()

# ----------------------------------------------------------------------
# 纯多进程入口函数 (由主进程通过 multiprocessing.Process 启动)
# ----------------------------------------------------------------------
def process_worker_entry(device_id: str, config_data: dict, log_queue: Queue, cmd_queue: Queue = None):
    """
    纯多进程模式下的子进程入口。
    而是直接运行一个完整的 asyncio 事件循环。
    """
    print(f"[SubProcess {device_id}] [{config_data}]进程启动 (PID: {os.getpid()})", file=sys.stderr)
    # 配置 Logger
    logger = logUtil.init_worker_logger_with_queue(device_id=device_id, log_queue=log_queue)

    # 1. 环境准备 (PYTHONPATH 等)
    if getattr(sys, 'frozen', False):
        root = get_project_root()
        libs_path = os.path.join(root, "_internal") if not os.path.exists(os.path.join(root, "libs")) else os.path.join(root, "libs")
        if os.path.exists(libs_path):
            current_pythonpath = os.environ.get('PYTHONPATH', '')
            os.environ['PYTHONPATH'] = f"{libs_path}{os.pathsep}{current_pythonpath}" if current_pythonpath else libs_path

    loop = None
    try:
        # 2. 创建独立的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 3. 实例化 Worker (传入 log_queue 用于回传日志)
        worker = WorkerLogicAsync(device_id, log_queue,cmd_queue,logger)

        # 4. 定义总控协程
        async def main_runner():
            worker._is_running = True
            logger.info("🚀 [MainRunner] 开始初始化...")

            # 创建后台监控任务
            monitor_task = asyncio.create_task(worker.monitor_loop())
            logger.info("👀 [MainRunner] 监控任务已创建")

            # 创建主业务任务
            business_task = asyncio.create_task(worker.start_task(config_data))
            logger.info("⚙️ [MainRunner] 业务任务已启动")

            try:
                # 等待任一任务结束
                done, pending = await asyncio.wait(
                    [business_task, monitor_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                # --- 清理逻辑 ---
                for task in pending:
                    task_name = "监控任务" if task == monitor_task else "业务任务"
                    logger.warning(f"🛑 正在取消未完成的任务：{task_name}")
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # 额外检查：如果是监控任务先结束（意味着收到了 stop 信号）
                # 此时 business_task 可能还在 run_in_executor 中跑（因为是同步阻塞代码）
                # cancel() 协程任务并不能直接杀死线程池里的线程。
                # 但只要 stop_event 被 set() 了，task_runner.py 里的循环应该会自己退出。
                if worker.stop_event.is_set():
                    logger.critical("⚡️ 检测到停止信号，等待业务线程自然退出...")
                    # 如果 business_task 还没 done，说明线程池里的代码还没返回
                    # 我们只能等待，或者设置一个超时强制放弃
                    if not business_task.done():
                        try:
                            # 最多再等 5 秒，防止死锁
                            await asyncio.wait_for(business_task, timeout=5.0)
                        except asyncio.TimeoutError:
                            logger.error("⚠️ 业务线程未在 5 秒内响应停止信号，可能存在阻塞！")
                        except asyncio.CancelledError:
                            pass

            except Exception as e:
                logger.error(f"💥 MainRunner 异常：{e}", exc_info=True)
            finally:
                worker._is_running = False
                logger.info("🏁 [MainRunner] 主运行器完全退出")

        # 5. 运行循环
        # ✅ 修复：调用时不需要传参
        loop.run_until_complete(main_runner())
        print(f"[SubProcess {device_id}] 任务正常结束", file=sys.stderr)
        return True

    except Exception as e:
        err_msg = f"[SubProcess {device_id}] 致命错误：{e}"
        print(err_msg, file=sys.stderr)
        # 尝试发送最后一条错误日志
        try:
            log_queue.put({'device_id': device_id, 'msg': str(e), 'level': 'CRITICAL'})
        except:
            pass
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 6. 清理
        if loop:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

# ----------------------------------------------------------------------
# 主进程调用示例 (仅供参考，实际在你的 UI 主逻辑中)
# ----------------------------------------------------------------------
# if __name__ == '__main__':
#     from multiprocessing import Process, Queue
#
#     log_q = Queue()
#     config = {"app_package": "com.example.app", "duration": 60}
#
#     # 启动子进程
#     p = Process(target=process_worker_entry, args=("EMULATOR-5554", config, log_q))
#     p.start()
#
#     # 主进程监听日志队列并更新 UI
#     while p.is_alive():
#         try:
#             log_item = log_q.get_nowait()
#             # update_ui(log_item['device_id'], log_item['msg'], log_item['level'])
#             print(f"UI Update: [{log_item['device_id']}] {log_item['level']}: {log_item['msg']}")
#         except:
#             pass
#         time.sleep(0.1)
#
#     p.join()