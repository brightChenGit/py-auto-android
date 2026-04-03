# cluster_page.py
from typing import Dict

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QFrame, QGridLayout,
                               QMessageBox, QSizePolicy, QApplication)
from PySide6.QtCore import Qt
from pyauto.utils.adb import AdbManager
from pyauto.page.card_page import DeviceCard
import pyauto.utils.logUtil


# 获取全局 logger 实例
logger = pyauto.utils.logUtil.get_logger()
# 常量
MAX_COLS = 3
CARD_MIN_HEIGHT = 800

class ClusterPage(QWidget):
    """投屏管理页面组件 (源自 main2.py)"""
    def __init__(self):
        super().__init__()
        self.devices: Dict[str, DeviceCard] = {}
        self.init_ui()



    def init_ui(self):
        # 使用 QVBoxLayout 作为主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- 工具栏区域 ---
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #f0f2f5; padding: 10px; border-bottom: 1px solid #ddd;")
        tb_layout = QHBoxLayout(toolbar)

        # 1. 刷新设备列表
        refresh_btn = QPushButton("刷新设备列表")
        refresh_btn.clicked.connect(self.scan_devices)
        refresh_btn.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px;")
        tb_layout.addWidget(refresh_btn)

        # 2. 重启 ADB 按钮
        restart_adb_btn = QPushButton("🔄 重启 ADB")
        restart_adb_btn.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px;")
        restart_adb_btn.setToolTip("执行 adb kill-server 和 adb start-server")
        restart_adb_btn.clicked.connect(self.handle_restart_adb)
        tb_layout.addWidget(restart_adb_btn)

        # 3. 一键启动所有
        start_all_btn = QPushButton("一键启动所有")
        start_all_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px 20px; border-radius: 4px;")
        start_all_btn.clicked.connect(self.start_all)
        tb_layout.addWidget(start_all_btn)

        # 4. 一键停止所有
        stop_all_btn = QPushButton("一键停止所有")
        stop_all_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px 20px; border-radius: 4px;")
        stop_all_btn.clicked.connect(self.stop_all)
        tb_layout.addWidget(stop_all_btn)

        main_layout.addWidget(toolbar)

        # --- 状态栏 ---
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("padding: 5px; color: #666;")
        main_layout.addWidget(self.status_label)


        # --- 滚动区域 (设备卡片) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("border: none;")

        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.container.setMinimumWidth(900)

        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)



    def handle_restart_adb(self):
        """处理重启 ADB 按钮点击事件"""
        self.status_label.setText("正在重启 ADB 服务...")
        QApplication.processEvents()

        success, message = AdbManager.restart_server()

        if success:
            self.status_label.setText("✅ " + message)
            QMessageBox.information(self, "成功", f"{message}\n\n建议点击'刷新设备列表'重新连接设备。")
        else:
            self.status_label.setText("❌ " + message)
            QMessageBox.critical(self, "错误", message)

    def scan_devices(self):
        """
        扫描并同步设备列表。
        【核心逻辑】只移除断开的设备，只添加新设备，保留正在运行的设备卡片。
        """
        self.status_label.setText("扫描中...")
        QApplication.processEvents()

        # 1. 获取当前真实的在线设备列表
        # 假设 AdbManager.get_devices() 返回的是 ['emulator-5554', ...]
        current_dev_ids = set(AdbManager.get_devices())

        if not current_dev_ids:
            self.status_label.setText("警告：未发现设备 (请检查 USB 连接或尝试重启 ADB)")
            # 注意：这里不要急着清空 UI，除非你确定用户想看到空界面
            # 如果想清空，可以调用 self._clear_all_cards()，但通常建议保留现场
            return

        # --- 第一步：移除已断开的设备 ---
        # 遍历当前字典中的设备，如果不在最新列表中，则移除
        for dev_id in list(self.devices.keys()):
            if dev_id not in current_dev_ids:
                card = self.devices.pop(dev_id)

                # 1. 从布局移除
                self.grid_layout.removeWidget(card)

                # 2. 停止该卡片的任务 (因为设备真断了)
                if hasattr(card, 'worker'):
                    card.worker.stop_task()
                if hasattr(card, 'stop_casting'):
                    card.stop_casting()

                # 3. 标记删除
                card.deleteLater()
                logger.info(f"设备 {dev_id} 断开，已移除卡片")

        # --- 第二步：添加新连接的设备 ---
        for dev_id in current_dev_ids:
            if dev_id not in self.devices:
                # 只有新设备才创建卡片
                card = DeviceCard(dev_id)
                card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                self.devices[dev_id] = card
                self.grid_layout.addWidget(card, 0, 0) # 先加进去，后面统一重排布局

        # --- 第三步：重新排列布局 (网格排序) ---
        # 因为中间可能删除了元素，现在的网格可能有空洞，需要重新整理位置
        self._rearrange_grid_layout()

        self.status_label.setText(f"已连接 {len(self.devices)} 台设备")

    def _rearrange_grid_layout(self):
        """
        重新计算网格布局的位置，确保没有空洞。
        """
        # 1. 先把所有 widget 从布局里拿出来 (但不删除对象)
        widgets = []
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                widgets.append(w)

        # 2. 按顺序重新放回去
        row, col = 0, 0
        max_col_used = 0

        for card in widgets:
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col > max_col_used: max_col_used = col
            if col >= MAX_COLS: # 确保 MAX_COLS 已定义
                col = 0
                row += 1

        # 3. 设置列拉伸
        for c in range(max_col_used):
            self.grid_layout.setColumnStretch(c, 1)

        # 4. 调整容器高度
        total_rows = row + 1 if col > 0 else row
        required_height = total_rows * (CARD_MIN_HEIGHT + 10) + 20
        self.container.setMinimumHeight(required_height)

    def get_config(self):
        return {
            "app_types": [x.strip() for x in self.app_input.text().split(",") if x.strip()],
            "op_types": [x.strip() for x in self.op_input.text().split(",") if x.strip()]
        }

    def start_all(self):
        for card in self.devices.values():
            card.handle_start_task()

        self.status_label.setText("所有设备已启动指令下发完毕")

    def stop_all(self):
        if not self.devices:
            return
        for card in self.devices.values():
            card.handle_stop_task()
        self.status_label.setText("所有设备已停止指令下发完毕")

    def showEvent(self, event):
        super().showEvent(event)
        # 如果希望每次切回首页自动刷新设备列表、
        self.scan_devices()
        # current_devices = self.get_connected_devices() # 获取当前连接的设备
        #
        # # 1. 移除已断开的设备
        # for dev_id in list(self.cards.keys()):
        #     if dev_id not in current_devices:
        #         card = self.cards.pop(dev_id)
        #         card.deleteLater() # 安全删除
        #         self.layout.removeWidget(card)
        #
        # # 2. 添加新设备
        # for dev_id in current_devices:
        #     if dev_id not in self.cards:
        #         new_card = DeviceCard(dev_id)
        #         self.cards[dev_id] = new_card
        #         self.layout.addWidget(new_card)

    # 3. 【关键】对于已存在的设备，【不要】做任何操作！
    # 让它们继续保持运行状态，UI 会自动显示它们（因为它们在 layout 里）