# 文件名: pyauto/scripts/web/main.py
from flask import Flask
from waitress import serve
import pyauto.utils.logUtil
# 1. 导入蓝图
from pyauto.scripts.web.sms_api import sms_bp
from pyauto.scripts.web.ocr_api import ocr_bp
from pyauto.utils.server_ocr_util import ServerOCRUtil

logger = pyauto.utils.logUtil.get_logger()

# 2. 创建 Flask 应用实例
app = Flask(__name__)

# 3. 注册蓝图
app.register_blueprint(sms_bp)
app.register_blueprint(ocr_bp)

def start_web_server():
    """
    这个函数只负责启动一次 Web 服务。
    它不再包含任何守护或重启逻辑。
    """
    try:
        logger.info("[WEB-SERVER] 正在预加载 OCR 模型...")
        ServerOCRUtil.get_engine()
        logger.info("[WEB-SERVER] 模型加载完成。")

        logger.info("[WEB-SERVER] 生产模式，使用 Waitress 服务器启动...")
        # 直接启动服务，这会阻塞当前进程，直到服务停止
        serve(app, host='0.0.0.0', port=8888, threads=8)
    except Exception as e:
        logger.error(f"[WEB-SERVER] 服务启动失败或运行中发生致命错误: {e}", exc_info=True)
        # 抛出异常，让父进程 (main.py) 知道服务已崩溃
        raise

# --- 程序入口 ---
if __name__ == '__main__':
    # 如果直接运行此文件，则直接启动服务
    start_web_server()