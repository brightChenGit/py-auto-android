# page/about_page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class AboutPage(QWidget):
    """项目说明页面"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- 1. 头部区域 ---
        header_layout = QHBoxLayout()

        title_label = QLabel("ℹ️ 项目说明")
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setStyleSheet("color: #001529;")
        header_layout.addWidget(title_label)

        # 占位符，保持标题在左侧
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # --- 2. 内容滚动区域 ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; }
            QScrollBar:vertical { 
                background: transparent; 
                width: 6px; 
                border-radius: 3px; 
                margin: 0; 
            }
            QScrollBar::handle:vertical { 
                background: #d9d9d9; 
                border-radius: 3px; 
                min-height: 20px; 
            }
        """)

        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 40) # 增加底部边距，防止内容被截断
        self.content_layout.setSpacing(20)

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

        # --- 3. 填充 README 内容 ---
        self._load_readme_content()

    def _load_readme_content(self):
        """加载并解析 README.md 的内容"""

        # 模拟 README.md 的内容 (为了保证独立运行，直接硬编码核心部分)
        # 在实际项目中，你也可以读取文件，但为了防止文件缺失导致崩溃，这里采用硬编码演示
        content_parts = [
            ("项目简介",
             "本项目是基于 <b>Python</b> 开发的<strong>通用安卓设备自动化操作框架</strong>，提供多设备管理、界面控制、屏幕识别、数据本地存储等基础能力。<br><br>"
             "<font color='#ff4d4f'><b>注意：</b></font> 本项目仅面向企业内部测试、设备运维与合法数据采集场景使用。"
             ),

            ("核心功能",
             "本框架提供以下核心能力：<br><br>"
             "✅ <b>多设备投屏中心</b>：支持投屏查看设备运行，每个设备单进程进行任务处理。<br>"
             "✅ <b>UI 自动化控制</b>：模拟点击、滑动、输入等操作，支持控件获取与页面结构解析。<br>"
             "✅ <b>视觉识别能力</b>：集成 OCR 文字识别与屏幕截图功能。<br>"
             "✅ <b>数据持久化</b>：支持结构化数据存储至 MySQL。<br>"
             "✅ <b>任务调度</b>：支持日志记录与异常处理。"
             ),

            ("技术栈",
             "项目基于以下技术构建：<br><br>"
             "• <b>Python 3.11.9</b><br>"
             "• <b>uiautomator2</b> & <b>uiautodev</b> (调试工具)<br>"
             "• <b>MySQL</b> 数据库<br>"
             "• <b>PaddleOCR</b> (PP-OCRv5 mobile 模型)<br>"
             "• <b>PySide6</b> (GUI 界面)"
             ),

            ("使用范围与责任声明",
             "<b>🔒 严格禁止行为：</b><br>"
             "1. 破解、逆向、Hook、抓包、绕过安全策略。<br>"
             "2. 批量高频访问、对服务端造成异常压力。<br>"
             "3. 采集用户隐私信息、个人信息、商业秘密。<br>"
             "4. 用于不正当竞争、数据倒卖、营销骚扰。<br><br>"

             "<b>📝 责任声明：</b><br>"
             "本项目仅提供基础自动化能力。使用者自行编写的业务脚本、采集规则、访问行为均由使用者独立负责。"
             ),

            ("联系方式",
             "如有任何问题，请通过以下方式联系：<br><br>"
             "📧 邮箱：<font color='#1890ff'><b>1024347104@qq.com</b></font><br>"
             "☕ 打赏地址：<a href='https://www.brightchen.top/pyauto/'>支持作者</a><br>"
             "github地址：<a href='https://github.com/brightChenGit/py-auto-android'>https://github.com/brightChenGit/py-auto-android</a><br>"
             "项目博客说明：<a href='https://www.brightchen.top/3494cdb3.html'>py-auto-android开源项目说明</a><br>"
             )
        ]

        # 动态生成控件
        for title, html_content in content_parts:
            section = self._create_section(title, html_content)
            self.content_layout.addWidget(section)

        self.content_layout.addStretch()

    def _create_section(self, title: str, content_html: str) -> QFrame:
        """创建一个标准的段落区块"""
        frame = QFrame()
        frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #e8e8e8;
                    border-radius: 8px;
                    padding: 20px;
                }
            """)
        frame_layout = QVBoxLayout(frame)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #001529; margin-bottom: 10px;")
        frame_layout.addWidget(title_label)

        # 内容
        content_label = QLabel()
        content_label.setWordWrap(True) # 允许自动换行
        content_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse) # 允许复制和点击链接
        content_label.setOpenExternalLinks(True) # 自动打开浏览器


        # 其他普通文本
        content_label.setText(content_html)

        # 设置样式
        content_label.setStyleSheet("font-size: 14px; color: #595959; line-height: 1.6;")
        frame_layout.addWidget(content_label)

        return frame
