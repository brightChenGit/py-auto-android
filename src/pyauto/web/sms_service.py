# 文件名: sms_service.py
from flask import Flask
from waitress import serve
import pyauto.utils.logUtil

# 1. 导入蓝图
from pyauto.web.sms_api import sms_bp

logger = pyauto.utils.logUtil.get_logger()

# 2. 创建 Flask 应用实例
app = Flask(__name__)

# 3. 注册蓝图
app.register_blueprint(sms_bp)

def start_sms_server():
    """启动短信服务"""
    try:
        logger.info("[SMS-SERVICE] 正在启动短信服务...")
        # 监听 8888 端口
        serve(app, host='0.0.0.0', port=8888, threads=4)
    except Exception as e:
        logger.error(f"[SMS-SERVICE] 服务启动失败: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    start_sms_server()