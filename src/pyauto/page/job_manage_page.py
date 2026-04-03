# page/job_manage_page.py
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QScrollArea, QFrame, QTextEdit, QLineEdit,
                               QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from pyauto.config.config_manager import DeviceConfigManager
from pyauto.utils.adb import AdbManager  # 确保路径正确，根据实际项目结构调整
import pyauto.utils.logUtil

# 获取全局 logger 实例
logger = pyauto.utils.logUtil.get_logger()
class KeyValueRow(QWidget):
    """
    优化的单行 Key-Value 组件
    """
    def __init__(self, key, value, on_delete_callback, parent=None):
        super().__init__(parent)
        self.key_input = None
        self.val_input = None
        self._init_ui(key, value, on_delete_callback)

    def _init_ui(self, key, value, on_delete_callback):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        self.key_input = QLineEdit(key)
        self.key_input.setFixedWidth(180)
        self.key_input.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.key_input.setStyleSheet("""
            QLineEdit {
                background-color: #f5f7fa;
                color: #606266;
                border: 1px solid #e4e7ed;
                border-radius: 4px;
                padding: 6px 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.key_input)

        if isinstance(value, list):
            val_str = ", ".join(str(v) for v in value)
        elif isinstance(value, (dict, bool, int, float)):
            val_str = str(value)
        else:
            val_str = str(value) if value is not None else ""

        self.val_input = QLineEdit(val_str)
        self.val_input.setPlaceholderText("输入值 (支持列表，用逗号分隔)")
        self.val_input.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                color: #303133;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #409EFF;
                box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
                outline: none;
            }
        """)
        layout.addWidget(self.val_input, stretch=1)

        self.del_btn = QPushButton("×")
        self.del_btn.setFixedSize(32, 32)
        self.del_btn.setToolTip("删除此字段")
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #909399;
                border: 1px solid #e4e7ed;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fef0f0;
                color: #f56c6c;
                border-color: #fde2e2;
            }
        """)
        self.del_btn.clicked.connect(lambda: on_delete_callback(self))
        layout.addWidget(self.del_btn)

class DeviceCard(QFrame):
    """单个设备的配置卡片 - 支持离线删除"""
    def __init__(self, device_id, config_data, is_connected=True, on_delete_callback=None, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.is_connected = is_connected
        self.on_delete_callback = on_delete_callback
        self.current_config = json.loads(json.dumps(config_data)) if config_data else {}
        self.is_json_view = False

        self.toggle_btn = None
        self.save_btn = None
        self.delete_config_btn = None # 新增：删除配置按钮
        self.json_edit = None
        self.kv_container_widget = None
        self.kv_rows = []

        self.setObjectName("deviceCard")

        # 根据在线/离线状态设置不同的边框颜色
        border_color = "#e8e8e8" if is_connected else "#ffcfcf" # 离线显示淡红色边框
        hover_color = "#1890ff" if is_connected else "#ff4d4f"

        self.setStyleSheet(f"""
            QFrame#deviceCard {{
                background-color: white;
                border: 1px solid {border_color};
                border-radius: 8px;
                margin: 10px;
                padding: 15px;
            }}
            QFrame#deviceCard:hover {{
                border-color: {hover_color};
                box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
            }}
        """)
        self.setMinimumHeight(280)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标题区域 (改为水平布局，以便放入删除按钮)
        header_layout = QHBoxLayout()

        status_text = " (在线)" if self.is_connected else " (离线 - 未连接)"
        status_color = "#52c41a" if self.is_connected else "#ff4d4f"

        title_label = QLabel(f"设备 ID: {self.device_id}{status_text}")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet(f"color: {status_color};")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 如果是离线设备，显示删除配置按钮
        if not self.is_connected and self.on_delete_callback:
            self.delete_config_btn = QPushButton("🗑️ 删除配置")
            self.delete_config_btn.setFixedHeight(30)
            self.delete_config_btn.setCursor(Qt.PointingHandCursor)
            self.delete_config_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fff1f0;
                    color: #ff4d4f;
                    border: 1px solid #ffa39e;
                    border-radius: 4px;
                    padding: 0 10px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #ff4d4f;
                    color: white;
                }
            """)
            self.delete_config_btn.clicked.connect(self._confirm_delete)
            header_layout.addWidget(self.delete_config_btn)

        layout.addLayout(header_layout)

        # 内容容器
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        layout.addWidget(self.content_frame)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.toggle_btn = QPushButton("转换JSON")
        self.toggle_btn.setFixedWidth(130)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f2f5;
                color: #333;
                border: none;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e6e8eb;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_view)

        self.save_btn = QPushButton("保存")
        self.save_btn.setFixedWidth(80)
        # 离线设备也可以保存配置修改（虽然没连接，但配置可以先存着）
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
        """)
        self.save_btn.clicked.connect(self.save_current_device)

        btn_layout.addWidget(self.toggle_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        self.render_kv_view()

    def _confirm_delete(self):
        """确认删除配置"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要从配置文件中删除设备 [{self.device_id}] 的配置吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes and self.on_delete_callback:
            self.on_delete_callback(self.device_id)

    def render_json_view(self):
        """渲染 JSON 文本框"""
        self.clear_layout(self.content_layout)
        self.kv_rows = []
        self.kv_container_widget = None

        self.json_edit = QTextEdit()
        self.json_edit.setPlainText(json.dumps(self.current_config, indent=4, ensure_ascii=False))
        self.json_edit.setFont(QFont("Consolas", 10))
        self.json_edit.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                color: #333;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 8px;
            }
            QTextEdit:focus {
                border-color: #1890ff;
            }
        """)
        self.content_layout.addWidget(self.json_edit)

        self.is_json_view = True
        if self.toggle_btn:
            self.toggle_btn.setText("转换键值")

    def render_kv_view(self):
        """渲染键值对表单"""
        self.clear_layout(self.content_layout)
        self.kv_rows = []

        self.kv_container_widget = QWidget()
        self.kv_form_layout = QVBoxLayout(self.kv_container_widget)
        self.kv_form_layout.setContentsMargins(0, 0, 0, 0)
        self.kv_form_layout.setSpacing(8)

        if not self.current_config:
            tip = QLabel("暂无配置项，请点击下方 + 添加字段 开始。")
            tip.setStyleSheet("color: #999; font-style: italic; padding: 10px;")
            self.kv_form_layout.addWidget(tip)
        else:
            for key, value in self.current_config.items():
                self._add_kv_row(key, value)

        add_btn = QPushButton("+ 添加字段")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1890ff;
                border: 2px dashed #d9d9d9;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                border-color: #1890ff;
                background-color: #e6f7ff;
            }
        """)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(lambda: self._add_kv_row("new_key", ""))
        self.kv_form_layout.addWidget(add_btn)

        self.kv_form_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.kv_container_widget)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
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
            QScrollBar::handle:vertical:hover {
                background: #bfbfbf;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        scroll_area.setMinimumHeight(120)
        scroll_area.setMaximumHeight(250)

        self.content_layout.addWidget(scroll_area)

        self.is_json_view = False
        if self.toggle_btn:
            self.toggle_btn.setText("转换JSON")

    def _add_kv_row(self, key, value):
        """添加一行 KV 组件"""
        row = KeyValueRow(key, value, self._remove_row)

        add_btn = None
        for i in range(self.kv_form_layout.count()):
            item = self.kv_form_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QPushButton) and item.widget().text() == "+ 添加字段":
                add_btn = item.widget()
                break

        if add_btn:
            index = self.kv_form_layout.indexOf(add_btn)
            self.kv_form_layout.insertWidget(index, row)
        else:
            self.kv_form_layout.addWidget(row)

        self.kv_rows.append(row)

    def _remove_row(self, row_widget):
        """删除某一行"""
        if row_widget in self.kv_rows:
            self.kv_rows.remove(row_widget)
            row_widget.deleteLater()

    def toggle_view(self):
        """切换视图并同步数据"""
        if not self.toggle_btn: return

        if self.is_json_view:
            try:
                text = self.json_edit.toPlainText()
                data = json.loads(text)
                if not isinstance(data, dict):
                    raise ValueError("根节点必须是对象 (Object)")
                self.current_config = data
                self.render_kv_view()
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "格式错误", f"JSON 解析失败:\n{e}")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))
        else:
            new_config = {}
            for row in self.kv_rows:
                k = row.key_input.text().strip()
                v_raw = row.val_input.text().strip()

                if not k: continue

                if ',' in v_raw:
                    v_list = [x.strip() for x in v_raw.split(',') if x.strip()]
                    new_config[k] = v_list
                else:
                    if v_raw.lower() == 'true': new_config[k] = True
                    elif v_raw.lower() == 'false': new_config[k] = False
                    elif v_raw.isdigit(): new_config[k] = int(v_raw)
                    elif self._is_float(v_raw): new_config[k] = float(v_raw)
                    else: new_config[k] = v_raw

            self.current_config = new_config
            self.render_json_view()

    def _is_float(self, s):
        try:
            float(s)
            return '.' in s
        except ValueError:
            return False

    def get_current_data(self):
        if self.is_json_view:
            if not self.json_edit: return None
            try:
                return json.loads(self.json_edit.toPlainText())
            except:
                return None
        else:
            new_config = {}
            for row in self.kv_rows:
                k = row.key_input.text().strip()
                v_raw = row.val_input.text().strip()
                if not k: continue

                if ',' in v_raw:
                    new_config[k] = [x.strip() for x in v_raw.split(',') if x.strip()]
                else:
                    if v_raw.lower() == 'true': new_config[k] = True
                    elif v_raw.lower() == 'false': new_config[k] = False
                    elif v_raw.isdigit(): new_config[k] = int(v_raw)
                    elif self._is_float(v_raw): new_config[k] = float(v_raw)
                    else: new_config[k] = v_raw
            return new_config

    def save_current_device(self):
        data = self.get_current_data()
        if data is None:
            QMessageBox.warning(self, "保存失败", "数据格式错误。")
            return

        if not isinstance(data, dict):
            QMessageBox.warning(self, "保存失败", "配置必须是 JSON 对象格式。")
            return

        DeviceConfigManager.save_config(self.device_id, data)
        status = "在线" if self.is_connected else "离线"
        QMessageBox.information(self, "成功", f"设备 {self.device_id} ({status}) 配置已保存！")

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class JobManagePage(QWidget):
    """功能管理页面 - 支持在线/离线设备管理及刷新"""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 头部布局
        header_layout = QHBoxLayout()
        title_label = QLabel("功能配置管理")
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setStyleSheet("color: #001529;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 新增：刷新设备按钮
        self.refresh_btn = QPushButton("🔄 刷新设备")
        self.refresh_btn.setFixedHeight(40)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1890ff;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 15px;
            }
            QPushButton:hover { background-color: #40a9ff; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_devices)
        header_layout.addWidget(self.refresh_btn)

        self.save_all_btn = QPushButton("💾 保存所有设备配置")
        self.save_all_btn.setFixedHeight(40)
        self.save_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #52c41a;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 4px;
                padding: 0 20px;
            }
            QPushButton:hover { background-color: #73d13d; }
        """)
        self.save_all_btn.clicked.connect(self.save_all_configs)
        header_layout.addWidget(self.save_all_btn)

        main_layout.addLayout(header_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        self.scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll_area)

        # 初始加载
        self.load_devices()

    def refresh_devices(self):
        """刷新设备列表"""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("扫描中...")
        # 强制重新扫描 ADB 设备
        self.load_devices()
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新设备")

    def load_devices(self):
        """
        核心逻辑：
        1. 加载所有已保存的配置 ID。
        2. 获取当前连接的 ADB 设备 ID。
        3. 合并列表：配置 ID + (连接 ID - 配置 ID)。
        4. 生成卡片：区分在线/离线状态。
        """
        self.clear_layout(self.cards_layout)

        # 1. 获取所有配置中的设备 ID
        config_manager = DeviceConfigManager()
        config_ids = list(config_manager._configs.keys())

        # 2. 获取当前实际连接的设备 ID
        connected_ids = AdbManager.get_devices()

        # 3. 构建最终展示的 ID 列表
        # 策略：先展示配置里有的（保持原有顺序），再追加新发现的设备
        displayed_ids = list(config_ids)
        for dev_id in connected_ids:
            if dev_id not in displayed_ids:
                displayed_ids.append(dev_id)

        if not displayed_ids:
            tip = QLabel("暂无设备配置，也未检测到任何连接的设备。\n请连接设备后点击'刷新设备'。")
            tip.setAlignment(Qt.AlignCenter)
            tip.setStyleSheet("color: #888; font-size: 16px; margin-top: 50px;")
            self.cards_layout.addWidget(tip)
            return

        # 4. 遍历生成卡片
        for device_id in displayed_ids:
            is_connected = device_id in connected_ids
            config_data = config_manager.get_config(device_id) # 获取配置，如果没有则返回空

            card = DeviceCard(
                device_id=device_id,
                config_data=config_data,
                is_connected=is_connected,
                on_delete_callback=self.handle_delete_device if not is_connected else None
            )
            # 离线设备不需要限制最大高度太死，或者保持原样
            card.setMaximumHeight(400)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def handle_delete_device(self, device_id):
        """处理删除离线设备配置"""
        try:
            config_manager = DeviceConfigManager()
            if device_id in config_manager._configs:
                del config_manager._configs[device_id]
                config_manager._save_configs()
                # 刷新列表
                self.load_devices()
                QMessageBox.information(self, "成功", f"设备 [{device_id}] 的配置已删除。")
            else:
                QMessageBox.warning(self, "错误", "设备配置不存在。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败：{str(e)}")

    def save_all_configs(self):
        success_count = 0
        fail_count = 0

        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), DeviceCard):
                card = item.widget()
                data = card.get_current_data()

                if isinstance(data, dict):
                    DeviceConfigManager.save_config(card.device_id, data)
                    success_count += 1
                else:
                    fail_count += 1

        msg = f"保存完成！\n成功：{success_count} 个设备\n"
        if fail_count > 0:
            msg += f"失败：{fail_count} 个设备 (格式错误)"
            QMessageBox.warning(self, "保存结果", msg)
        else:
            QMessageBox.information(self, "保存结果", msg)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()