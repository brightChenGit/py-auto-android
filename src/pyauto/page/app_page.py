# app_runner.py
import sys
import webbrowser
import asyncio

# --- 这里可以安全地导入所有重型依赖了，因为只有主程序会运行这里 ---
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QStackedWidget, QLabel, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# 导入页面
from pyauto.page.cluster_page import ClusterPage
from pyauto.page.job_manage_page import JobManagePage
from pyauto.page.about_page import AboutPage
from qasync import QEventLoop

# 导入日志 (只有主程序会初始化)
import pyauto.utils.logUtil
logger = pyauto.utils.logUtil.get_logger()

class AndroidViewPage(QWidget):
    """UI 控件管理页面"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel("UI 控件管理页面\n\n(功能开发中...)")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 16))
        label.setStyleSheet("color: #888;")
        layout.addWidget(label)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能投屏管理系统")
        self.setGeometry(100, 100, 1600, 1000)

        # 样式表 (保持不变)
        self.setStyleSheet("""
            QMainWindow { background-color: #ffffff; }
            QPushButton {
                background-color: transparent; color: #333; border: none;
                padding: 15px 20px; text-align: left; font-size: 16px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #e6f7ff; color: #1890ff; }
            QPushButton:checked { 
                background-color: #e6f7ff; color: #1890ff; font-weight: bold;
                border-left: 4px solid #1890ff;
            }
            QFrame#sidebar { background-color: #f5f5f5; border-right: 1px solid #e8e8e8; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)
        sidebar_layout.setSpacing(5)

        title_label = QLabel("  投屏中心")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet("color: #001529; padding: 10px 0 20px 10px;")
        sidebar_layout.addWidget(title_label)

        self.btn_cluster = QPushButton("📱 投屏管理 (首页)")
        self.btn_function = QPushButton("📅 任务管理")
        self.btn_android_view = QPushButton("📅 UI 控件管理")
        # self.btn_donate = QPushButton("💰 打赏作者")
        # 在 __init__ 方法中
        self.btn_about = QPushButton("ℹ️ 关于项目") # 在按钮定义部分






        for btn in [self.btn_cluster, self.btn_function, self.btn_android_view]:
            btn.setCheckable(True)

        self.btn_cluster.setChecked(True)

        for btn in [self.btn_cluster, self.btn_function, self.btn_android_view,
                    # self.btn_donate
                    self.btn_about

                    ]:
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()
        # self.btn_donate.clicked.connect(self.open_donate_url)

        # 右侧内容
        self.stacked_widget = QStackedWidget()
        self.cluster_page = ClusterPage()
        self.android_view_page = AndroidViewPage()
        self.function_page = JobManagePage()
        self.about_page = AboutPage()


        self.stacked_widget.addWidget(self.cluster_page)
        self.stacked_widget.addWidget(self.function_page)
        self.stacked_widget.addWidget(self.android_view_page)


        # 在连接信号槽的部分 (switch_page附近)


        # 在 stacked_widget 添加页面的部分

        self.stacked_widget.addWidget(self.about_page)


        self.btn_cluster.clicked.connect(lambda: self.switch_page(0))
        self.btn_function.clicked.connect(lambda: self.switch_page(1))
        self.btn_android_view.clicked.connect(lambda: self.switch_page(2))
        self.btn_about.clicked.connect(lambda: self.switch_page(3)) # 假设它是第4个页面

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stacked_widget)

    def open_donate_url(self):
        webbrowser.open("https://www.brightchen.top/pyauto/")

    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        buttons = [self.btn_cluster, self.btn_function, self.btn_android_view,self.btn_about]
        for i, btn in enumerate(buttons):
            btn.setChecked(i == index)

def run_main_app():
    """主程序启动入口函数"""
    logger.info("主程序启动...")

    # 只有在这里才创建 QApplication
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # 3. 【关键步骤】创建 qasync 的事件循环并绑定到 app
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()

    # 这样 create_task 创建的任务才会被 Qt 事件循环调度执行
    with loop:
        # 如果你的 MainWindow 有异步初始化方法 (如 startup)，可以在这里调用
        # loop.run_until_complete(window.startup())

        # 直接运行 Qt 事件循环，qasync 会自动处理 asyncio 任务
        loop.run_until_complete(app.exec_())