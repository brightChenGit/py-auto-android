# adb.py
import re
import subprocess
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple, Optional
import pyauto.utils.logUtil
from io import BytesIO
from PIL import Image

# 获取全局 logger 实例
logger = pyauto.utils.logUtil.get_logger()

class AdbManager:
    """ADB 服务管理工具类 - 统一使用项目内 bin/adb.exe"""

    # 类变量缓存 adb 路径，避免重复计算
    _adb_path: Optional[str] = None

    @classmethod
    def get_adb_path(cls) -> str:
        """
        获取 adb 可执行文件的绝对路径。
        优先级：
        1. PyInstaller 打包目录 (_MEIPASS)/bin/adb.exe
        2. 当前脚本同级目录/bin/adb.exe
        3. 当前脚本上级目录/bin/adb.exe
        4. 当前工作目录/bin/adb.exe
        5. 系统环境变量中的 adb
        """
        if cls._adb_path:
            return cls._adb_path

        try:
            candidates = []

            # 1. PyInstaller 打包环境
            base_path = getattr(sys, '_MEIPASS', None)
            if base_path:
                candidates.append(os.path.join(str(base_path), 'bin', 'adb.exe'))

            # 获取当前文件绝对路径对象
            current_file = Path(__file__).resolve()
            current_dir = str(current_file.parent)

            # 2. 当前脚本同级目录
            candidates.append(os.path.join(current_dir, 'bin', 'adb.exe'))

            # 3. 当前脚本上级目录 (安全获取)
            parent_path = current_file.parent.parent
            # 防止根目录再向上找导致路径异常，确保 parent 和 current 不同
            if str(parent_path) != current_dir:
                candidates.append(os.path.join(str(parent_path), 'bin', 'adb.exe'))

            # 4. 当前工作目录
            candidates.append(os.path.join(str(Path.cwd()), 'bin', 'adb.exe'))

            # 遍历候选路径
            for candidate in candidates:
                #  修复：使用 os.path.exists 检查字符串路径
                if os.path.exists(candidate):
                    cls._adb_path = candidate
                    logger.info(f" 找到内置 adb: {candidate}")
                    return cls._adb_path

            # 如果所有内置路径都没找到，尝试调用系统 adb
            logger.info("未在项目中找到内置 adb，尝试检测系统环境变量中的 adb...")
            # 如果都没找到，回退到系统 adb
            # 检查系统是否有 adb
            startupinfo = None
            creationflags = 0
            # 仅在 Windows 系统下配置
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW

            subprocess.run(['adb', 'version'], capture_output=True, check=False, startupinfo=startupinfo, creationflags=creationflags)
            cls._adb_path = 'adb'
            logger.info(f"警告：未在项目中找到 bin/adb.exe，将使用系统环境变量中的 adb。")
            return cls._adb_path

        except Exception as e:
            # 极端情况下，直接返回 'adb' 让 subprocess 去环境变量找
            logger.info(f"{e}")
            cls._adb_path = 'adb'
            return cls._adb_path

    @classmethod
    def _run_adb_command(cls, args: List[str], timeout: int = 10, device_id: Optional[str] = None) -> Tuple[bool, str, bytes]:
        """
        内部统一执行 ADB 命令的方法
        :param args: 命令参数列表 (不包含 'adb' 和 '-s device')
        :param timeout: 超时时间
        :param device_id: 设备 ID，如果提供则添加 -s 参数
        :return: (success, error_message, stdout_bytes)
        """
        cmd = [cls.get_adb_path()]
        if device_id:
            cmd.extend(['-s', device_id])

        cmd.extend(args)
        startupinfo = None
        creationflags = 0

        # 仅在 Windows 系统下配置
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                check=False,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            if res.returncode == 0:
                return True, "", res.stdout
            else:
                err_msg = res.stderr.decode('utf-8', errors='ignore').strip()
                return False, err_msg, b""
        except subprocess.TimeoutExpired:
            return False, f"命令执行超时 ({timeout}s)", b""
        except FileNotFoundError:
            return False, "未找到 adb 可执行文件", b""
        except Exception as e:
            return False, str(e), b""

    @staticmethod
    def restart_server() -> Tuple[bool, str]:
        """
        重启 ADB 服务
        返回: (成功与否, 消息内容)
        """
        manager = AdbManager()

        # 1. 杀死服务
        success, err, _ = manager._run_adb_command(['kill-server'], timeout=10)
        if not success and "server not running" not in err.lower():
            pass

        # 2. 启动服务
        success, err, out = manager._run_adb_command(['start-server'], timeout=10)

        if success:
            return True, "ADB 服务已重启成功"
        else:
            return False, f"ADB 重启失败：{err}"


    @staticmethod
    def get_devices() -> List[str]:
        def natural_sort_key(s):
            """用于自然排序的 Key 函数"""
            return [(int(text) if text.isdigit() else text.lower()) for text in re.split(r'(\d+)', s)]

        """
        获取当前连接的设备列表
        返回：设备 ID 列表
        """
        manager = AdbManager()
        success, err, out = manager._run_adb_command(['devices'], timeout=5)

        if not success:
            return []

        lines = out.decode('utf-8', errors='ignore').splitlines()
        # 跳过第一行标题 "List of devices attached"
        if len(lines) > 1:
            lines = lines[1:]
        else:
            return []

        devices = []
        for line in lines:
            line = line.strip()
            if line and '\tdevice' in line:
                device_id = line.split('\t')[0]
                devices.append(device_id)
        # 使用自然排序
        devices.sort(key=natural_sort_key)
        return devices


    @staticmethod
    def set_tcpip_port(port: int, device_id: str) -> Tuple[bool, str]:
        """
        设置设备进入 TCP/IP 监听模式
        :param port: 端口号 (通常为 5555)
        :param device_id: 设备 ID
        :return: (success, message)
        """
        manager = AdbManager()
        success, err, _ = manager._run_adb_command(
            ['tcpip', str(port)],
            device_id=device_id,
            timeout=10
        )
        if success:
            return True, "设置 TCP/IP 模式成功"
        else:
            return False, f"设置失败: {err}"

    @staticmethod
    def connect_wifi(ip: str, port: int = 5555, timeout: int = 5) -> Tuple[bool, str]:
        """
        连接指定 IP 和端口的设备 (WiFi 连接)
        :param ip: 设备 IP 地址
        :param port: 端口号
        :param timeout: 超时时间
        :return: (success, message)
        """
        manager = AdbManager()
        target = f"{ip}:{port}"
        success, err, _ = manager._run_adb_command(
            ['connect', target],
            timeout=timeout
        )
        if success:
            return True, f"连接 {target} 成功"
        else:
            return False, f"连接 {target} 失败: {err}"

    @staticmethod
    def get_screen_capture(device_id: str, timeout: int = 5, compress_quality: int = 50) -> Tuple[bool, str, bytes]:
        """
        获取设备屏幕截图并直接在源头进行压缩 (转换为 JPG)。
        对应原 card_page.py 中的：adb -s <id> exec-out screencap -p

        :param device_id: 设备 ID
        :param timeout: 超时时间
        :param compress_quality: JPEG 压缩质量 (1-100)，默认 85。数值越小压缩越大，画质越低。
                                 如果设置为 100 或 None，则保留原始 PNG (不压缩)。
        :return: (success, error_message, image_data_bytes)
        """
        manager = AdbManager()
        # 命令：exec-out screencap -p (获取原始 PNG 流)
        success, err, data = manager._run_adb_command(
            ['exec-out', 'screencap', '-p'],
            timeout=timeout,
            device_id=device_id
        )

        if not success or not data:
            if not success:
                if "device not found" in err.lower() or "no devices" in err.lower():
                    return False, f"设备 {device_id} 未找到", b""
                return False, err, b""
            return False, "截图数据为空", b""

        # --- 新增：源头压缩逻辑 ---
        if  compress_quality and 0 < compress_quality < 100:
            try:
                # 将字节流加载为图片对象
                img = Image.open(BytesIO(data))

                # 如果原图是 RGBA (PNG 常见)，转为 RGB 以兼容 JPEG
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # 保存到新的字节流，格式为 JPEG
                output_buffer = BytesIO()
                img.save(output_buffer, format="JPEG", quality=compress_quality, optimize=True)

                # 获取压缩后的数据
                compressed_data = output_buffer.getvalue()

                logger.debug(f"截图已压缩：原始 {len(data)} 字节 -> 压缩后 {len(compressed_data)} 字节 (质量:{compress_quality})")
                return True, "", compressed_data

            except Exception as e:
                logger.warning(f"图片压缩失败，返回原始数据：{str(e)}")
                # 如果压缩失败，降级返回原始 PNG 数据，保证流程不中断
                return True, "", data
        # -----------------------

        # 如果未安装 PIL 或未开启压缩，返回原始 PNG 数据
        return True, "", data

    @staticmethod
    def shell_command(device_id: str, command: str, timeout: int = 5) -> Tuple[bool, str, str]:
        """
        执行 ADB Shell 命令
        :param device_id: 设备 ID
        :param command: shell 命令字符串
        :param timeout: 超时时间
        :return: (success, error_message, output_text)
        """
        manager = AdbManager()
        success, err, out = manager._run_adb_command(
            ['shell', command],
            timeout=timeout,
            device_id=device_id
        )

        if success:
            return True, "", out.decode('utf-8', errors='ignore').strip()
        else:
            return False, err, ""

    @classmethod
    def get_device_ip(cls, device_id: str) -> Optional[str]:
        """
        获取指定设备的 WiFi IP 地址
        """
        manager = cls()
        # 使用 ip addr show wlan0 命令
        success, err, out = manager._run_adb_command(
            ['shell', 'ip', 'addr', 'show', 'wlan0'],
            device_id=device_id
        )

        if success and out:
            output = out.decode('utf-8', errors='ignore')
            # 正则匹配 IPv4
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
            if match:
                ip = match.group(1)
                if not ip.startswith("169.254"): # 排除无效 IP
                    return ip
        return None

    @staticmethod
    def usb_to_wifi(device_id: str) -> Tuple[bool, str]:
        """全自动 USB 切 WiFi"""
        logger.info(f"🚀 开始执行 USB 切 WiFi: {device_id}")

        # 1. 获取 IP
        ip = AdbManager.get_device_ip(device_id)
        if not ip:
            return False, "获取 IP 失败，请确保手机已连接 WiFi"

        logger.info(f"📱 设备 IP: {ip}")

        # 2. 开启 TCP/IP 模式
        success, msg = AdbManager.set_tcpip_port(5555, device_id)
        if not success:
            return False, f"开启 TCP/IP 模式失败: {msg}"

        # 3. 等待设备重启 ADB 服务
        logger.info("⏳ 等待设备切换端口...")
        time.sleep(2)

        # 4. 尝试连接 WiFi
        for i in range(3):
            success, msg = AdbManager.connect_wifi(ip, 5555)
            if success:
                logger.info(f"✅ 成功切换到 WiFi: {ip}:5555")
                return True, ip
            logger.warning(f"⚠️ 第 {i+1} 次连接尝试失败: {msg}，重试中...")
            time.sleep(1)

        return False, "WiFi 连接超时或失败（模拟器不支持转wifi）"

def get_adb_executable() -> str:
    """
    获取 adb 可执行文件的绝对路径。
    优先使用项目根目录下的 ./bin/adb.exe
    """
    return AdbManager.get_adb_path()

# 测试代码 (可选)
if __name__ == "__main__":
    logger.info(f"当前使用的 ADB 路径：{AdbManager.get_adb_path()}")
    devs = AdbManager.get_devices()
    logger.info(f"连接的设备：{devs}")

    if devs:
        dev = devs[0]
        logger.info(f"正在获取设备 {dev} 的截图 (带压缩)...")
        # 这里默认使用 85 的质量进行压缩
        ok, msg, data = AdbManager.get_screen_capture(dev, compress_quality=30)
        if ok:
            logger.info(f"截图成功，大小：{len(data)} 字节")
        else:
            logger.warn(f"截图失败：{msg}")