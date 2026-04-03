
# page/card_page.py

import time
import threading
from typing import Optional
from concurrent.futures import Future
from multiprocessing import Queue, Process # 引入 Queue

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy,
                               QWidget, QTextEdit, QPlainTextEdit)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap, QFont, QTextCursor, QColor

from pyauto.config.config_manager import DeviceConfigManager
from pyauto.core.worker_logic import process_worker_entry
from pyauto.utils.adb import AdbManager
import pyauto.utils.logUtil

# 获取全局 logger 实例
logger =  pyauto.utils.logUtil.get_logger()

def log_raw_message(logger_instance, message):
    """
    直接使用 logger 的底层流输出消息，跳过所有格式化（无前缀、无时间戳）。
    """
    for handler in logger_instance.handlers:
        if hasattr(handler, 'stream') and handler.stream:
            try:
                handler.acquire()
                handler.stream.write(str(message) + '\n')
                handler.flush()
            except Exception:
                pass
            finally:
                handler.release()

class ScreenCaptureThread(QThread):
    """纯截图线程"""
    image_ready = Signal(bytes)
    error_occurred = Signal(str)
    log_signal = Signal(str, str)

    def __init__(self, device_id: str, interval: float = 1.0):
        super().__init__()
        self.device_id = device_id
        self.interval = interval
        self._running = False
        self.current_future: Optional[Future] = None
        self.thread_id = id(self)
        self.log_message(f"📸 截图线程已创建，内存ID: {self.thread_id}", "SYS")

    def run(self):
        self._running = True
        self.log_message(f"截图线程已启动 (间隔 {self.interval}s)", "SYS")

        while self._running:
            try:
                success, err_msg, png_data = AdbManager.get_screen_capture(
                    device_id=self.device_id,
                    timeout=int(self.interval) + 2
                )
                if success and png_data and self._running:
                    self.image_ready.emit(png_data)
                elif self._running:
                    err_lower = err_msg.lower()
                    if "device not found" in err_lower or "no devices" in err_lower or "unauthorized" in err_lower:
                        self.log_message(f"设备 {self.device_id} 已断开或未授权", "ERROR")
                        self._running = False
                        break
                    elif err_msg and int(time.time()) % 10 == 0:
                        self.log_message(f"ADB 截图响应异常：{err_msg[:50]}", "WARN")
                time.sleep(self.interval)
            except Exception as e:
                if self._running:
                    self.log_message(f"截图线程发生未知错误：{str(e)}", "ERROR")
                time.sleep(1)

        self.log_message(f"设备 {self.device_id} 截图线程已停止,内存ID{self.thread_id}", "INFO")

    def stop(self):
        self._running = False
        self.wait(500)

    def log_message(self, message: str, level: str = "INFO"):
        self.log_signal.emit(message, level)
        logger.info(message)

class WifiSwitchWorker(QThread):
    # 定义信号：传递 (success, message) 或 (success, ip)
    result_signal = Signal(bool, str)

    def __init__(self, device_id):
        super().__init__()
        self.device_id = device_id

    def run(self):
        """在后台线程执行耗时的切换操作"""
        # 调用你之前封装好的方法
        success, message = AdbManager.usb_to_wifi(self.device_id)
        # 发射结果信号
        self.result_signal.emit(success, message)

class DeviceCard(QFrame):
    """
    设备卡片：
    1. 顶部：标题 + 状态
    2. 中部：屏幕投屏区
    3. 下部：控制按钮
    4. 底部：日志输出区
    """
    log_signal = Signal(str, str)

    def __init__(self, device_id: str):
        super().__init__()
        self.device_id = device_id
        self.screen_thread: Optional[ScreenCaptureThread] = None

        self.worker_process = None
        self.current_future: Optional[Future] = None

        # 【新增】多进程通信队列
        self.log_queue: Optional[Queue] = None
        self.cmd_queue: Optional[Queue] = None

        # 【新增】日志监听线程
        self.log_listener_thread: Optional[threading.Thread] = None
        self._stop_log_listener = False

        self.is_casting = False
        self.current_config: dict = {}

        self.init_ui()
        self.setStyleSheet("""
            DeviceCard {
                background-color: white; 
                border: 1px solid #ddd; 
                border-radius: 8px;
                padding: 10px;
            }
            DeviceCard:hover { border: 1px solid #17a2b8; }
        """)

        self.log_signal.connect(self._update_log_ui)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # --- 1. 标题与状态栏 ---
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel(f"<b>{self.device_id}</b>")
        self.lbl_title.setStyleSheet("font-size: 14px; color: #333;")
        self.lbl_title.setMaximumHeight(40)
        header_layout.addWidget(self.lbl_title)

        self.lbl_task_info = QLabel("未配置任务")
        self.lbl_task_info.setStyleSheet("font-size: 12px; color: #666; margin-left: 10px; font-style: italic;")
        self.lbl_task_info.setAlignment(Qt.AlignVCenter)
        self.lbl_task_info.setMaximumHeight(40)
        self.lbl_task_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.set_config()
        self.lbl_task_info.setText(f"● {self.current_config}")
        header_layout.addWidget(self.lbl_task_info)

        self.lbl_status = QLabel("● 就绪")
        self.lbl_status.setStyleSheet("color: #666; font-size: 12px;")
        self.lbl_status.setMaximumHeight(40)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_status)

        main_layout.addLayout(header_layout)

        # --- 2. 屏幕显示区域 ---
        self.screen_container = QWidget()
        self.screen_container.setStyleSheet("background-color: #000; border-radius: 4px;")
        screen_layout = QVBoxLayout(self.screen_container)
        screen_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_screen = QLabel("点击'开启投屏'查看实时画面")
        self.lbl_screen.setAlignment(Qt.AlignCenter)
        self.lbl_screen.setStyleSheet("color: #888;")
        self.lbl_screen.setMinimumHeight(250)
        self.lbl_screen.setMinimumWidth(300)
        self.lbl_screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        screen_layout.addWidget(self.lbl_screen)
        main_layout.addWidget(self.screen_container)

        # --- 3. 控制按钮区 ---
        btn_layout = QHBoxLayout()

        self.btn_cast = QPushButton("📺开启投屏")
        self.btn_cast.setCheckable(True)
        self.btn_cast.setStyleSheet(self._get_btn_style("#17a2b8"))
        self.btn_cast.clicked.connect(self.toggle_casting)
        btn_layout.addWidget(self.btn_cast)

        btn_layout.addStretch()

        # 【新增】切换 WiFi 按钮
        self.btn_switch_wifi = QPushButton("📡转WiFi")
        self.btn_switch_wifi.setStyleSheet(self._get_btn_style("#6f42c1")) # 紫色风格
        self.btn_switch_wifi.clicked.connect(self.handle_switch_to_wifi)
        if self.is_wifi_device():
            self.lbl_title.setText(f"<b>{self.device_id}")
            self.btn_switch_wifi.setText("WiFi")
            self.btn_switch_wifi.setEnabled(False)
            self.log_message("检测到设备已通过 WiFi 连接", "SYS")
        btn_layout.addWidget(self.btn_switch_wifi)

        self.btn_start = QPushButton("▶启动任务")
        self.btn_start.setStyleSheet(self._get_btn_style("#28a745"))
        self.btn_start.clicked.connect(self.handle_start_task)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹停止任务")
        self.btn_stop.setStyleSheet(self._get_btn_style("#dc3545"))
        self.btn_stop.clicked.connect(self.handle_stop_task)
        btn_layout.addWidget(self.btn_stop)

        main_layout.addLayout(btn_layout)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2d2d2d;
                color: #00ff00;
                border: none;
                padding: 4px;
                outline: none;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                border: none;
                background: #2d2d2d;
                height: 8px;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #555555;
                border: none;
                border-radius: 4px;
                min-height: 20px;
                min-width: 20px;
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background: #666666;
            }
            QScrollBar::handle:vertical:pressed, QScrollBar::handle:horizontal:pressed {
                background: #888888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
                background: transparent;
            }
            QScrollBar::corner {
                background: #2d2d2d;
            }
        """)
        self.log_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._update_log_ui(f"等待指令...", "SYS")

        main_layout.addWidget(self.log_text)

    def _get_btn_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color}; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;
            }}
            QPushButton:hover {{ filter: brightness(110%); }}
            QPushButton:disabled {{ background-color: #ccc; color: #666; }}
        """

    @Slot(str, str)
    def _update_log_ui(self, message: str, level: str):
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.appendPlainText(f"[{level}]"+message)

        color_map = {
            "ERROR": "#ff6b6b",
            "WARN": "#feca57",
            "SYS": "#48dbfb",
            "INFO": "#00ff00"
        }
        color_name = color_map.get(level, "#00ff00")

        last_block = self.log_text.document().lastBlock()
        selection = QTextEdit.ExtraSelection()
        selection.cursor = QTextCursor(last_block)
        selection.cursor.select(QTextCursor.BlockUnderCursor)

        fmt = selection.format
        fmt.setForeground(QColor(color_name))
        selection.format = fmt
        self.log_text.setExtraSelections([selection])

        doc = self.log_text.document()
        max_lines = 1000
        delete_count = 500
        current_blocks = doc.blockCount()

        if current_blocks > max_lines:
            cursor = self.log_text.textCursor()
            cursor.beginEditBlock()
            try:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                lines_to_delete = min(delete_count, current_blocks - 1)
                for _ in range(lines_to_delete):
                    if cursor.atEnd(): break
                    cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor)
                delete_end_pos = cursor.position()
                cursor.movePosition(QTextCursor.Start)
                cursor.setPosition(delete_end_pos, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
            finally:
                cursor.endEditBlock()

        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # console_msg = f"[{self.device_id}] {message}"
        # log_raw_message(logger, console_msg)

    def log_message(self, message: str, level: str = "INFO"):
        self.log_signal.emit(message, level)

    # ================= 投屏逻辑 =================

    def toggle_casting(self, checked: bool):
        if checked:
            self.stop_casting()
        else:
            self.start_casting()

    def start_casting(self):
        if self.screen_thread and self.screen_thread.isRunning():
            self.screen_thread.stop()

        self.is_casting = True
        self.btn_cast.setChecked(False)
        self.btn_cast.setText("⏹关闭投屏")
        self.btn_cast.setStyleSheet(self._get_btn_style("#dc3545"))
        self.lbl_screen.setText("正在连接屏幕...")
        self.lbl_screen.setStyleSheet("color: #666;")

        self.log_message(f"{self.device_id}正在启动屏幕镜像...", "SYS")

        self.screen_thread = ScreenCaptureThread(self.device_id, interval=0.2)
        self.screen_thread.image_ready.connect(self.update_screen_image)
        self.screen_thread.error_occurred.connect(self.on_cast_error)
        self.screen_thread.log_signal.connect(self.log_message)
        self.screen_thread.start()

    def stop_casting(self):
        if self.screen_thread:
            self.screen_thread.stop()
            self.screen_thread = None

        self.btn_cast.setText("📺开启投屏")
        self.btn_cast.setStyleSheet(self._get_btn_style("#17a2b8"))
        self.btn_cast.setChecked(True)
        self.lbl_screen.setText("投屏已关闭")
        self.lbl_screen.setStyleSheet("color: #888;")
        self.log_message("屏幕镜像已停止", "SYS")

    def update_screen_image(self, png_data: bytes):
        if not self.is_casting or not png_data:
            return

         # 【优化】先清除旧引用
        self.lbl_screen.clear()
        pixmap = QPixmap()
        if not pixmap.loadFromData(png_data):
            return

        target_size = self.lbl_screen.size()
        if target_size.isEmpty():
            self.lbl_screen.setPixmap(pixmap)
            self.lbl_screen.setText("")
            return

        self._current_scaled_pixmap = pixmap.scaled(
            target_size,
            Qt.KeepAspectRatio,
            #快速变换
            Qt.FastTransformation
            #平滑变换
            # Qt.SmoothTransformation
        )
        self.lbl_screen.setPixmap(self._current_scaled_pixmap)
        self.lbl_screen.setText("")

    def on_cast_error(self, msg: str):
        self.stop_casting()
        self.log_message(msg, "ERROR")


    # ================= usb切换wifi逻辑 (核心优化区) =================
    def handle_switch_to_wifi(self):
        if not self.device_id:
            self.log_message("设备 ID 未知", "ERROR")
            return

        # --- 关键修改：禁用按钮并启动线程 ---
        self.btn_switch_wifi.setEnabled(False)
        self.btn_switch_wifi.setText("🔄切换中...")

        # 1. 实例化 Worker
        self.wifi_worker = WifiSwitchWorker(self.device_id)
        # 2. 连接 Worker 的结果信号到处理函数
        self.wifi_worker.result_signal.connect(self.on_wifi_switch_finished)
        # 3. 启动线程 (start() 会自动调用 run())
        self.wifi_worker.start()

    def on_wifi_switch_finished(self, success, message):
        """
        这个函数在子线程结束后，自动在主线程（UI线程）被调用
        用来更新 UI 状态
        """
        # 恢复按钮状态
        self.btn_switch_wifi.setEnabled(True)

        if success:
            wifi_ip = message
            self.log_message(f"🎉 切换成功！IP: {wifi_ip}", "SYS")
            self.log_message(f"🎉 切换成功！请拔掉对应手机usb再点击'刷新设备列表'按钮", "SYS")
            self.lbl_title.setText(f"<b>{self.device_id}")
            self.btn_switch_wifi.setText("✅已切换")
            self.btn_switch_wifi.setEnabled(False) # 成功后禁用，防止重复操作
            self.btn_switch_wifi.setText("WIFI")
        else:
            self.log_message(f"❌ 切换失败: {message}", "ERROR")
            self.btn_switch_wifi.setText("📡转WIFI")

    # ================= 业务逻辑 (核心优化区) =================

    def set_config(self):
        self.current_config = DeviceConfigManager.get_config(self.device_id)

    def is_wifi_device(self) -> bool:
        """
        通过设备 ID 格式判断是否为 WiFi 设备
        """
        return ":" in self.device_id and "." in self.device_id

    def _start_log_listener(self, queue: Queue):
        """启动后台线程监听子进程日志队列"""
        def listen():
            while not self._stop_log_listener:
                try:
                    # 非阻塞获取，超时 0.5 秒以便检查停止标志
                    msg = queue.get(timeout=0.5)
                    # 发射信号到 UI 主线程
                    self.log_signal.emit(f"{msg['msg']}", msg['level'])
                except:
                    # 队列空或超时，继续循环
                    continue

        self._stop_log_listener = False
        self.log_listener_thread = threading.Thread(target=listen, daemon=True)
        self.log_listener_thread.start()

    def _stop_log_listener(self):
        """停止日志监听线程"""
        self._stop_log_listener = True
        if self.log_listener_thread and self.log_listener_thread.is_alive():
            self.log_listener_thread.join(timeout=1.0)

    def handle_start_task(self):
        """处理启动按钮 - 使用 multiprocessing.Process"""
        latest_config = DeviceConfigManager.get_config(self.device_id)
        if not latest_config:
            latest_config = {"key": "未配置", "device_id": self.device_id}
        # else:
        #     latest_config['device_id'] = self.device_id
        #

        self.update_lbl_task_info(f"{latest_config}")
        # 检查是否已经在运行
        if self.worker_process and self.worker_process.is_alive():
            self.log_message(f"{self.device_id}任务已经在运行中 (PID: {self.worker_process.pid})", "WARN")
            self.update_status("运行中", "#ffc107")
            return

        # 1. 清理旧资源
        self._cleanup_worker_resources()

        # 2. 创建新队列
        self.log_queue = Queue()
        self.cmd_queue = Queue()

        # 3. 启动日志监听线程
        self._start_log_listener(self.log_queue)

        self.log_message(f"{self.device_id}正在启动独立子进程...", "INFO")
        self.update_status("任务启动中...", "#28a745")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        # 4. 创建并启动进程
        # 注意：target 必须是可 pickled 的顶层函数
        self.worker_process = Process(
            target=process_worker_entry,
            args=(self.device_id, latest_config, self.log_queue, self.cmd_queue),
            daemon=False # 设置为 False，让主进程退出时可以选择等待或单独处理
        )

        try:
            self.worker_process.start()
            self.log_message(f"✅ {self.device_id}子进程已启动 (PID: {self.worker_process.pid})", "SYS")

            # 启动一个监控线程来检测进程意外退出
            self._start_process_monitor()

        except Exception as e:
            self.log_message(f"💥 {self.device_id}启动子进程失败：{e}", "ERROR")
            self._cleanup_worker_resources()
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def _start_process_monitor(self):
        """后台监控子进程是否意外退出"""
        def monitor():
            if self.worker_process:
                self.worker_process.join() # 阻塞直到进程结束
                if self.worker_process.exitcode != 0:
                    # 必须在 UI 线程更新，所以用 signal 或 QTimer，这里简化直接用 log_signal (假设已连接)
                    # 由于这是子线程，不能直接操作 UI，log_signal 是安全的
                    self.log_message(f"⚠️ {self.device_id}子进程意外退出 (代码: {self.worker_process.exitcode})", "ERROR")

                # 进程结束后重置 UI 状态
                # 注意：这里需要确保在 UI 线程执行，Qt 的信号槽机制会自动处理
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
                self.update_status("已停止", "#666")
                self._cleanup_worker_resources()

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    def handle_stop_task(self):
        """处理停止 - 先软停止，超时后硬杀死"""
        if not self.worker_process or not self.worker_process.is_alive():
            self.log_message(f"{self.device_id}没有正在运行的任务", "WARN")
            self.update_status("已停止", "#666")
            return

        # 1. 尝试软停止 (发送 Queue 指令)
        if self.cmd_queue:
            try:
                self.cmd_queue.put_nowait({'action': 'stop', 'device_id': self.device_id})
                self.log_message(f"🛑 {self.device_id}已发送停止指令，等待子进程优雅退出...", "SYS")
            except Exception as e:
                self.log_message(f"{self.device_id}发送指令失败：{e}", "ERROR")

        # 2. 启动一个临时线程等待进程退出，如果超时则 Kill
        def wait_and_kill():
            # 等待最多 5 秒
            self.worker_process.join(timeout=5.0)

            if self.worker_process.is_alive():
                self.log_message(f"⚠️ {self.device_id}子进程未响应停止指令，正在强制杀死...", "WARN")
                try:
                    self.worker_process.terminate() # 发送 SIGTERM
                    self.worker_process.join(timeout=2.0)
                    if self.worker_process.is_alive():
                        self.worker_process.kill() # 发送 SIGKILL (Windows 上 terminate 即 kill)
                        self.worker_process.join()
                    self.log_signal.emit(f"💀 {self.device_id}子进程已被强制杀死", "ERROR")
                except Exception as e:
                    self.log_signal.emit(f"{self.device_id}强制杀死失败：{e}", "ERROR")
            else:
                self.log_signal.emit(f"✅ {self.device_id}子进程已正常退出", "INFO")

            # 更新 UI 状态 (通过信号或直接调用，需确保线程安全，这里依赖 log_signal 触发后续清理或手动调用)
            # 简单起见，可以在这里直接调用 cleanup，但要小心 UI 操作
            # 最好还是依赖 process monitor 线程或者在这里发射一个自定义信号
            # 为了简化，我们假设上面的 log 发出后，用户能看到，实际清理逻辑最好在 monitor 里统一做
            # 这里手动触发一下清理逻辑的状态重置
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.update_status("已停止", "#666")
            # 注意：不要在这里直接调用 _cleanup_worker_resources 删除 queue，
            # 因为 monitor 线程可能还在用，或者 process 刚退出来还没完全收尾。
            # 最安全的做法是让 monitor 线程去调用 cleanup。

        thread = threading.Thread(target=wait_and_kill, daemon=True)
        thread.start()

    def update_lbl_task_info(self, text: str):
        self.lbl_task_info.setText(f"● {text}")
        # self.lbl_task_info.setStyleSheet(f"color: {color}; font-weight: bold;")

    def update_status(self, text: str, color: str):
        self.lbl_status.setText(f"● {text}")
        self.lbl_status.setStyleSheet(f"color: {color}; font-weight: bold;")

    # ================= 生命周期管理 =================

    def _cleanup_worker_resources(self):
        """清理所有与 worker 相关的资源"""
        self._stop_log_listener = True

        # 关闭队列
        if self.cmd_queue:
            try: self.cmd_queue.close()
            except: pass
            self.cmd_queue = None

        if self.log_queue:
            try: self.log_queue.close()
            except: pass
            self.log_queue = None

        # 等待监听线程退出
        if self.log_listener_thread and self.log_listener_thread.is_alive():
            self.log_listener_thread.join(timeout=1.0)
        self.log_listener_thread = None

        # 进程对象保留引用以便检查 exitcode，但逻辑上认为它已结束
        # 如果进程还在跑（异常情况），这里不应该强行置空，应由 stop 逻辑处理
        if self.worker_process and not self.worker_process.is_alive():
            self.worker_process = None
    def hideEvent(self, event):
        super().hideEvent(event)
        if self.screen_thread and self.screen_thread.isRunning():
            self.screen_thread.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self.start_casting()

    def closeEvent(self, event):
        self.is_casting = False
        if self.screen_thread:
            self.screen_thread.stop()
            self.screen_thread = None

        # 强制处理 Worker 进程
        if self.worker_process and self.worker_process.is_alive():
            self.log_message(f"{self.device_id}窗口关闭，正在终止子进程...", "WARN")
            if self.cmd_queue:
                try: self.cmd_queue.put_nowait({'action': 'stop'})
                except: pass

            self.worker_process.join(timeout=3.0)
            if self.worker_process.is_alive():
                self.worker_process.terminate()
                self.worker_process.join(timeout=2.0)
                if self.worker_process.is_alive():
                    self.worker_process.kill()

        self._cleanup_worker_resources()
        super().closeEvent(event)
