# page/sms_page.py
import socket
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QClipboard, QGuiApplication

class SmsPage(QWidget):
    """短信转发配置说明页面"""

    def __init__(self):
        super().__init__()
        self.local_ip = self._get_local_ip()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- 1. 头部区域 ---
        header_layout = QHBoxLayout()
        title_label = QLabel("📡 短信webhook配置")
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setStyleSheet("color: #001529;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --- 2. 内容滚动区域 ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; }
            QScrollBar:vertical { background: transparent; width: 6px; border-radius: 3px; margin: 0; }
            QScrollBar::handle:vertical { background: #d9d9d9; border-radius: 3px; min-height: 20px; }
        """)

        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 40)
        self.content_layout.setSpacing(20)
        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

        # --- 3. 填充配置内容 ---
        self._load_config_content()

    def _get_local_ip(self):
        """获取本机局域网IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 8))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _show_copy_feedback(self, button):
        """
        显示复制成功的反馈信息。
        将按钮文本临时改为“复制成功”，2秒后自动恢复。
        """
        original_text = button.text()
        button.setText("✅ 复制成功")
        button.setEnabled(False)  # 短暂禁用，防止重复点击

        # 使用 QTimer 在2000毫秒（2秒）后执行恢复操作
        QTimer.singleShot(2000, lambda: self._reset_button_text(button, original_text))

    def _reset_button_text(self, button, text):
        """恢复按钮的原始文本和状态"""
        button.setText(text)
        button.setEnabled(True)

    def _load_config_content(self):
        """加载配置说明内容"""

        # 1. 本地服务地址
        server_url = f"http://{self.local_ip}:8888/sms"
        self.content_layout.addWidget(self._create_copy_section(
            "* 🖥️ 本地接收地址",
            "请在短信转发器APP（如 SmsForwarder）中配置 Webhook 或 HTTP 请求时，填写以下地址作为服务器 URL：",
            server_url
        ))
        job_json=""""app_phone": 具体手机号,
"app_login": true"""
        self.content_layout.addWidget(self._create_copy_section("* 📝 任务管理菜单配置自动登录参数","app_phone 为自动登录时的手机号，有则进入自动填写手机号流程，无则不进入自动登录流程<br>"
                                                                                                 "app_login 为true时支持验证码自动获取及填写到app上，其余为人工处理短信验证码<br>"
                                                                                                 "任务管理菜单自动登录参数配置参考:", job_json))
        # 3. 消息模板
        template_json = """{
  "phone": "{{CARD_SLOT}}",
  "content": "{{MSG}}",
"timestamp": "{{RECEIVE_TIME}}"
}"""
        self.content_layout.addWidget(self._create_copy_section(
            "📦 消息模板 (JSON)",
            "如果您的转发器支持自定义消息体（Body），请使用以下 JSON 格式，以便后端正确解析：",
            template_json
        ))

        self.content_layout.addStretch()

        # 2. 正则表达式参考 (已更新)
        regex_content = f"【滴滴出行】.*验证码|【新电途】.*验证码"
        self.content_layout.addWidget(self._create_copy_section("📝 正则表达式","为了提取验证码，建议在转发器中配置正则表达式。<br>"
                                                                               "通用验证码匹配 (4-6位数字): <code style='background:#f0f0f0; padding:2px 4px; border-radius:4px;'>\\d{4,6}</code><br>"
                                                                               "常见关键词匹配: <code style='background:#f0f0f0; padding:2px 4px; border-radius:4px;'>验证码[是:：]?\\s*(\\d{4,6})</code><br>"
                                                                               "<font color='#faad14'>提示：</font><br> "
                                                                               "当前正则表达式参考:", regex_content))



    def _create_copy_section(self, title: str, description: str, text_to_copy: str) -> QFrame:
        """创建一个带复制按钮的区块"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { 
                background-color: white; 
                border: 1px solid #e8e8e8; 
                border-radius: 8px; 
                padding: 20px; 
            }
        """)
        layout = QVBoxLayout(frame)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #001529; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # 描述
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 14px; color: #595959; margin-bottom: 15px;")
        layout.addWidget(desc_label)

        # 内容显示框
        content_display = QLabel(text_to_copy)
        content_display.setWordWrap(True)
        content_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_display.setStyleSheet("""
            background-color: #f5f5f5; 
            border: 1px solid #d9d9d9; 
            border-radius: 4px; 
            padding: 10px; 
            font-family: Consolas, monospace;
            font-size: 13px;
            color: #262626;
        """)
        layout.addWidget(content_display)

        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        copy_btn = QPushButton("📋 复制内容")
        copy_btn.setFixedWidth(100)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #40a9ff; }
            QPushButton:pressed { background-color: #096dd9; }
            QPushButton:disabled { background-color: #91d5ff; color: #fff; }
        """)
        # 使用 lambda 绑定点击事件，先复制再显示反馈
        copy_btn.clicked.connect(lambda: self._copy_and_feedback(text_to_copy, copy_btn))
        btn_layout.addWidget(copy_btn)

        layout.addLayout(btn_layout)
        return frame

    def _copy_and_feedback(self, text, button):
        """执行复制操作并显示反馈"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        self._show_copy_feedback(button)

    def _create_section(self, title: str, html_content: str) -> QFrame:
        """创建一个标准的段落区块（无复制按钮，仅用于说明）"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { 
                background-color: white; 
                border: 1px solid #e8e8e8; 
                border-radius: 8px; 
                padding: 20px; 
            }
        """)
        layout = QVBoxLayout(frame)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #001529; margin-bottom: 10px;")
        layout.addWidget(title_label)

        content_label = QLabel()
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        content_label.setOpenExternalLinks(True)
        content_label.setText(html_content)
        content_label.setStyleSheet("font-size: 14px; color: #595959; line-height: 1.6;")
        layout.addWidget(content_label)

        return frame