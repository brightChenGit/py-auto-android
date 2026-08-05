# 文件名: ocr_service.py
from flask import Flask
from waitress import serve
import pyauto.utils.logUtil
from pyauto.web.ocr_api import ocr_bp
from pyauto.utils.server_ocr_util import ServerOCRUtil

logger = pyauto.utils.logUtil.get_logger()

app = Flask(__name__)
app.register_blueprint(ocr_bp)
## 服务拆分多端口的原因：ocr服务存在内存泄露，自动重启时不牵扯到其他服务
def start_ocr_server():
    """启动 OCR 服务"""
    try:
        logger.info("[OCR-SERVICE] 正在预加载 OCR 模型...")
        ServerOCRUtil.get_engine()
        logger.info("[OCR-SERVICE] 模型加载完成。")

        logger.info("[OCR-SERVICE] 正在启动 OCR 服务...")
        serve(app, host='0.0.0.0', port=8889, threads=4)
    except Exception as e:
        logger.error(f"[OCR-SERVICE] 服务启动失败: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    start_ocr_server()