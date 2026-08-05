# page/config_base_page.py
import json
import socket
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QPushButton, QLineEdit, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from pyauto.config.config_base import UnifiedConfigManager
from pyauto.utils.custom_dialog import ModernDialog


class ConfigBasePage(QWidget):
    """配置管理页面 - 布局修复版"""

    def showEvent(self, event):
        """当页面显示时，自动重新加载配置"""
        super().showEvent(event)
        self.reload_config()

    def reload_config(self):
        """重新加载配置并更新界面显示"""
        try:
            # 1. 从文件加载最新数据到内存
            self.config_base._load_configs()
            # 2. 重新获取所有配置
            ocr_config = self.config_base.get_config('ocr') or {}
            email_config = self.config_base.get_config('email') or {}
            mysql_config = self.config_base.get_config('mysql') or {}
            local_name = self.config_base.get_config('local_name')


            # 3. 更新本地电脑名称
            if 'local_name' in self.inputs:
                default_name = socket.gethostname()
                self.inputs['local_name'].setText(local_name if local_name else default_name)


            if 'bool_auto_stop' in self.checkboxes:
                self.checkboxes['bool_auto_stop'].setChecked(bool(self.config_base.get_config('bool_auto_stop', False)))
            # 4. 更新 OCR 复选框
            if 'use_cuda' in self.checkboxes:
                self.checkboxes['use_cuda'].setChecked(bool(ocr_config.get('use_cuda', False)))
            if 'use_dml' in self.checkboxes:
                self.checkboxes['use_dml'].setChecked(bool(ocr_config.get('use_dml', False)))

            # 5. 更新邮件输入框
            for key, widget in self.inputs.items():
                if key.startswith('email_'):
                    json_key = key.replace('email_', '')
                    val = email_config.get(json_key, '')
                    # 根据控件类型设置状态
                    if isinstance(widget, QCheckBox):
                        widget.setChecked(bool(val))
                    else:
                        widget.setText(str(val))
                elif key.startswith('mysql_'):
                    json_key = key.replace('mysql_', '')
                    val = mysql_config.get(json_key, '')
                    widget.setText(str(val))

        except Exception as e:
            print(f"重新加载配置时出错: {e}")

    def __init__(self):
        super().__init__()
        self.config_base = UnifiedConfigManager()
        # 存储控件引用以便保存时读取
        self.inputs = {}
        self.checkboxes = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- 1. 头部区域 (标题 + 保存按钮) ---
        header_layout = QHBoxLayout()
        title_label = QLabel("⚙️ 应用配置")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        save_btn = QPushButton("💾 保存配置")
        save_btn.setFixedHeight(36)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; border: none; border-radius: 6px; padding: 0 15px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3e8e41; }
        """)
        save_btn.clicked.connect(self.save_config)
        header_layout.addWidget(save_btn)
        main_layout.addLayout(header_layout)

        # --- 2. 内容滚动区域 ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)

        # 【修改点1】调整卡片添加顺序
        content_layout.addWidget(self._create_basic_card())
        content_layout.addWidget(self._create_ocr_card())
        content_layout.addWidget(self._create_email_card())
        # 【修改点2】新增 MySQL 配置卡片
        content_layout.addWidget(self._create_mysql_card())
        content_layout.addWidget(self._create_setting_card())

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def _create_basic_card(self):
        """创建基础配置卡片"""
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("#card { background: white; border-radius: 8px; border: 1px solid #eee; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)

        title = QLabel("💻 基础信息")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title)

        row = QHBoxLayout()
        label = QLabel("本地电脑名称")
        label.setFixedWidth(120)
        input_name = QLineEdit()
        self.inputs['local_name'] = input_name
        row.addWidget(label)
        row.addWidget(input_name)
        layout.addLayout(row)
        return card

    def _create_ocr_card(self):
        """创建 OCR 配置卡片"""
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("#card { background: white; border-radius: 8px; border: 1px solid #eee; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)

        title = QLabel("👁️ OCR 识别加速配置（默认内存识别）")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title)

        # 选项 1: CUDA
        row1 = QHBoxLayout()
        cb_cuda = QCheckBox("启用 CUDA (NVIDIA显卡加速)")
        self.checkboxes['use_cuda'] = cb_cuda
        row1.addWidget(cb_cuda)
        row1.addStretch()
        layout.addLayout(row1)
        row1.itemAt(0).widget().hide()

        # 选项 2: DML
        row2 = QHBoxLayout()
        cb_dml = QCheckBox("启用 DML (需要独显)")
        self.checkboxes['use_dml'] = cb_dml
        row2.addWidget(cb_dml)
        row2.addStretch()
        layout.addLayout(row2)
        return card

    def _create_email_card(self):
        """创建邮件配置卡片"""
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("#card { background: white; border-radius: 8px; border: 1px solid #eee; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)

        title = QLabel("📧 邮件服务配置")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title)

        fields = [
            ('email_smtp_host', 'SMTP 服务器地址', 'smtp.qq.com', 'smtp_host'),
            ('email_smtp_port', 'SMTP 端口', '465', 'smtp_port'),
            ('email_sender_email', '发送者邮箱', '', 'sender_email'),
            ('email_auth_code', '授权码/密码', '', 'auth_code'),
            ('email_receiver_email', '接收者邮箱', '多个,分割', 'receiver_email'),
            ('email_task_start', '任务开始邮件', True, 'task_start'),
            ('email_task_end', '任务结束邮件', True, 'task_end'),
            ('email_task_error', '任务异常邮件', True, 'task_error'),
            ('email_task_manual', '任务转人工邮件', True, 'task_manual'),
            ('email_task_captcha', '任务验证码邮件', True, 'task_captcha'),
        ]
        for widget_key, label_text, placeholder, json_key in fields:
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(120)
            # input_box = QLineEdit()
            # input_box.setPlaceholderText(placeholder)
            # if widget_key == 'email_auth_code':
            #     input_box.setEchoMode(QLineEdit.PasswordEchoOnEdit)
            # 根据配置项类型选择控件
            if widget_key in ['email_task_start', 'email_task_end', 'email_task_error', 'email_task_manual', 'email_task_captcha']:
                input_box = QCheckBox()
            else:
                input_box = QLineEdit()
                input_box.setPlaceholderText(placeholder)
                if widget_key == 'email_auth_code':
                    input_box.setEchoMode(QLineEdit.PasswordEchoOnEdit)

            self.inputs[widget_key] = input_box
            row.addWidget(label)
            row.addWidget(input_box)
            layout.addLayout(row)
        return card

    # 【修改点3】新增创建 MySQL 配置卡片的方法
    def _create_mysql_card(self):
        """创建 MySQL 配置卡片"""
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("#card { background: white; border-radius: 8px; border: 1px solid #eee; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)

        title = QLabel("🗄️ MySQL 数据库配置")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title)

        fields = [
            ('mysql_host', '服务器地址', 'localhost', 'host'),
            ('mysql_port', '端口', '3306', 'port'),
            ('mysql_user', '用户名', 'root', 'user'),
            ('mysql_password', '密码', '', 'password'),
            ('mysql_database', '数据库名', '', 'database')
        ]
        for widget_key, label_text, placeholder, json_key in fields:
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(120)
            input_box = QLineEdit()
            input_box.setPlaceholderText(placeholder)
            if widget_key == 'mysql_password':
                input_box.setEchoMode(QLineEdit.PasswordEchoOnEdit)
            self.inputs[widget_key] = input_box
            row.addWidget(label)
            row.addWidget(input_box)
            layout.addLayout(row)
        return card



    def _create_setting_card(self):
        """创建 OCR 配置卡片"""
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("#card { background: white; border-radius: 8px; border: 1px solid #eee; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)

        title = QLabel("其他配置")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title)

        # 选项 1: 任务自动停止
        row = QHBoxLayout()
        cb_stop = QCheckBox("任务空闲自动停止")
        self.checkboxes['bool_auto_stop'] = cb_stop
        row.addWidget(cb_stop)
        row.addStretch()
        layout.addLayout(row)
        return card


    def save_config(self):
        """保存配置到 JSON (使用 set_all_config)"""
        try:
            current_config = {}
            current_config['bool_auto_stop'] = self.checkboxes.get('bool_auto_stop').isChecked()
            # 1. 构建新的 OCR 配置块
            new_ocr_config = {
                "use_cuda": self.checkboxes.get('use_cuda').isChecked(),
                "use_dml": self.checkboxes.get('use_dml').isChecked()
            }
            # 2. 构建新的 Email 配置块
            new_email_config = {}
            # 3. 构建新的 MySQL 配置块
            new_mysql_config = {}

            for key, widget in self.inputs.items():
                if key.startswith("email_"):
                    json_key = key.replace("email_", "")
                    # 根据控件类型获取值
                    if isinstance(widget, QCheckBox):
                        new_email_config[json_key] = widget.isChecked()
                    else:
                        new_email_config[json_key] = widget.text().strip()
                elif key.startswith("mysql_"):
                    json_key = key.replace("mysql_", "")
                    new_mysql_config[json_key] = widget.text().strip()
                elif key == "local_name":
                    current_config['local_name'] = widget.text().strip()

            # 4. 更新主配置字典
            current_config["ocr"] = new_ocr_config
            current_config["email"] = new_email_config
            current_config["mysql"] = new_mysql_config

            # 5. 调用 set_all_config 写入文件
            self.config_base.set_all_config(current_config)
            # QMessageBox.information(self, "成功", "配置成功")
            # 调用自定义弹窗
            dialog = ModernDialog(
                title="配置成功",
                message="配置已生效！",
                type="success",  # 可选: success, error, info
                parent=self      # 传入 parent 确保弹窗在主窗口之上
            )
            dialog.exec()
        except Exception as e:
            # QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")
            dialog = ModernDialog(
                title="错误",
                message=f"保存失败:\n{str(e)}",
                type="error",  # 可选: success, error, info
                parent=self      # 传入 parent 确保弹窗在主窗口之上
            )
            dialog.exec()