from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QMainWindow, QWidget, QHBoxLayout


# ==========================================
# 1. 自定义弹窗类 (ModernDialog)
# ==========================================
class ModernDialog(QDialog):
    """
    支持 type 参数的自定义弹窗
    type: "success" (绿), "error" (红), "info" (蓝/灰)
    """
    def __init__(self, title="提示", message="", type="info", parent=None):
        super().__init__(parent)

        # --- 基础设置 ---
        self.setWindowTitle(title)
        self.setMinimumWidth(300)
        # 去掉标题栏 + 置顶 + 任务栏不显示(可选)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        # 关键：开启背景透明，以便实现圆角
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # --- 布局与容器 ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.content_frame = QFrame()
        self.content_frame.setObjectName("ContentFrame")
        # 将 type 属性绑定到 Frame 上，供 CSS 选择器使用
        self.content_frame.setProperty("type", type)

        frame_layout = QVBoxLayout(self.content_frame)
        frame_layout.setContentsMargins(40, 30, 40, 30)
        frame_layout.setSpacing(20)

        # --- 内容控件 ---
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("TitleLabel")

        msg_label = QLabel(message)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        msg_label.setWordWrap(True) # 允许自动换行
        msg_label.setObjectName("MsgLabel")

        btn_ok = QPushButton("确定")
        btn_ok.setObjectName("OkButton")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(self.accept)

        frame_layout.addWidget(title_label)
        frame_layout.addWidget(msg_label)
        frame_layout.addSpacing(10)
        frame_layout.addWidget(btn_ok)

        main_layout.addWidget(self.content_frame)

        # --- 样式表 (QSS) ---
        self.setStyleSheet("""
            QDialog { background-color: transparent; }

            /* 默认白色卡片 */
            #ContentFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }

            /* 根据 type 属性改变边框颜色 */
            #ContentFrame[type="success"] { border: 2px solid #00C08B; }
            #ContentFrame[type="error"]   { border: 2px solid #FF5252; }
            #ContentFrame[type="info"]    { border: 2px solid #2196F3; }

            #TitleLabel { color: #333333; font-size: 20px; font-weight: bold; font-family: "Microsoft YaHei"; }
            #MsgLabel   { color: #666666; font-size: 14px; line-height: 22px; }

            /* 按钮基础样式 */
            #OkButton {
                border: none; border-radius: 6px; padding: 10px 0;
                font-size: 15px; font-weight: bold; color: white;
                 text-align: center; 
            }

            /* 根据 type 属性改变按钮颜色 */
            #ContentFrame[type="success"] #OkButton { background-color: #00C08B; }
            #ContentFrame[type="success"] #OkButton:hover { background-color: #00A878; }

            #ContentFrame[type="error"] #OkButton   { background-color: #FF5252; }
            #ContentFrame[type="error"] #OkButton:hover   { background-color: #E04848; }

            #ContentFrame[type="info"] #OkButton    { background-color: #2196F3; }
            #ContentFrame[type="info"] #OkButton:hover    { background-color: #1976D2; }
        """)

# ==========================================
# 2. 测试用的主窗口
# ==========================================
class MainWindowModernDialog(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ModernDialog 测试")
        self.resize(400, 300)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 按钮 1：成功提示
        btn_success = QPushButton("弹出【配置成功】弹窗")
        btn_success.clicked.connect(self.show_success_dialog)

        # 按钮 2：错误提示
        btn_error = QPushButton("弹出【删除失败】弹窗")
        btn_error.clicked.connect(self.show_error_dialog)

        # 按钮 3：普通信息
        btn_info = QPushButton("弹出【普通提示】弹窗")
        btn_info.clicked.connect(self.show_info_dialog)

        layout.addWidget(btn_success)
        layout.addWidget(btn_error)
        layout.addWidget(btn_info)

    def show_success_dialog(self):
        """模拟你之前的配置成功场景"""
        dialog = ModernDialog(
            title="配置成功",
            message="新的数据库和 OCR 配置已生效！\n系统将在重启后应用所有更改。",
            type="success",  # 关键参数
            parent=self
        )
        dialog.exec()

    def show_error_dialog(self):
        """模拟错误场景"""
        dialog = ModernDialog(
            title="操作失败",
            message="无法连接到远程服务器。\n请检查网络设置或联系管理员。",
            type="error",    # 关键参数
            parent=self
        )
        dialog.exec()

    def show_info_dialog(self):
        """模拟普通信息场景"""
        dialog = ModernDialog(
            title="系统更新",
            message="检测到新版本 v2.0.1。\n是否现在前往下载？",
            type="info",     # 关键参数
            parent=self
        )
        dialog.exec()
# ==========================================
# 1. 自定义双按钮弹窗类
# ==========================================
class ConfirmDialog(QDialog):
    """
    自定义确认弹窗，替代 QMessageBox.question
    结构优化：采用 ModernDialog 的样式管理方式，使用属性选择器。
    包含：标题、自动换行的正文、[取消] 和 [确认] 两个按钮
    """
    def __init__(self, title="提示", message="", parent=None):
        super().__init__(parent)

        # --- 窗口基础设置 ---
        self.setWindowTitle(title)
        # 去掉系统标题栏 + 置顶
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        # 关键：开启背景透明，以便实现圆角
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # --- 布局与容器 ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 使用 QFrame 作为内容卡片容器
        self.content_frame = QFrame()
        self.content_frame.setObjectName("ContentFrame")

        # 主布局
        frame_layout = QVBoxLayout(self.content_frame)
        frame_layout.setContentsMargins(40, 30, 40, 30) # 统一内边距
        frame_layout.setSpacing(20)

        # --- 内容控件 ---
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("TitleLabel")

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)  # 允许自动换行
        msg_label.setAlignment(Qt.AlignmentFlag.AlignLeft) # 文字居中看起来更协调
        msg_label.setObjectName("MsgLabel")

        # --- 按钮区域 ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setObjectName("CancelButton")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("确认")
        self.btn_confirm.setObjectName("ConfirmButton")
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.clicked.connect(self.accept)

        # 将按钮加入布局
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)

        # 将所有控件加入主布局
        frame_layout.addWidget(title_label)
        frame_layout.addWidget(msg_label)
        frame_layout.addLayout(btn_layout)

        main_layout.addWidget(self.content_frame)

        # --- 样式表 (QSS) ---
        # 样式全部集中在这里，通过 objectName 和属性选择器管理，非常清晰
        self.setStyleSheet("""
            /* 对话框背景透明 */
            QDialog {
                background-color: transparent;
            }

            /* --- 卡片容器样式 --- */
            #ContentFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 2px solid #00C08B; /* 默认绿色边框 */
            }

            /* --- 文本样式 --- */
            #TitleLabel {
                color: #333333;
                font-size: 20px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }

            #MsgLabel {
                color: #666666;
                font-size: 14px;
                line-height: 22px;
            }

            /* --- 按钮基础样式 --- */
            /* 为两个按钮设置相同的尺寸策略，让它们平分宽度，实现完美居中 */
            #CancelButton, #ConfirmButton {
                border: none;
                border-radius: 6px;
                padding: 10px 0;
                font-size: 15px;
                font-weight: bold;
                color: white;
                text-align: center;
            }

            /* --- 取消按钮特定样式 --- */
            #CancelButton {
                background-color: #f5f5f5;
                color: #333333;
            }
            #CancelButton:hover {
                background-color: #e0e0e0;
            }

            /* --- 确认按钮特定样式 --- */
            #ConfirmButton {
                background-color: #00C08B;
            }
            #ConfirmButton:hover {
                background-color: #00A878;
            }
        """)

# ==========================================
# 2. 模拟主窗口 (用于测试调用)
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("主程序")
        self.resize(400, 300)

        btn = QPushButton("点击删除配置", self)
        btn.setGeometry(100, 100, 200, 40)
        btn.clicked.connect(self.delete_config)

    def delete_config(self):
        # --- 调用自定义弹窗 ---
        dialog = ConfirmDialog(
            title="确认删除",
            message="确定要从配置文件中删除设备 [Device-001] 的配置吗？\n此操作不可恢复。",
            parent=self
        )

        # exec() 会阻塞在这里，直到用户点击按钮
        result = dialog.exec()

        # --- 判断结果 ---
        # QDialog.Accepted (确认) 或 QDialog.Rejected (取消)
        if result == QDialog.DialogCode.Accepted:
            print("用户点击了【确认】 -> 执行删除逻辑")
            # TODO: 在这里写你的删除代码
        else:
            print("用户点击了【取消】 -> 什么都不做")

# 测试代码
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 全局字体设置 (可选，让界面更好看)
    font = app.font()
    font.setFamily("Microsoft YaHei")
    app.setFont(font)
    #
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


    # 设置全局字体（可选，让界面更好看）

    # window = MainWindowModernDialog()
    # window.show()
    #
    # sys.exit(app.exec())