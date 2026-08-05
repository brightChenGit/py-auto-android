# 文件名：sms_api.py
import re
from flask import Blueprint, request, jsonify
import pyauto.utils.logUtil
from pyauto.config.config_sms import SmsConfigManager


# 1. 创建一个名为 'sms_bp' 的蓝图
sms_bp = Blueprint('sms', __name__)

logger =  pyauto.utils.logUtil.get_logger()

def extract_app_name(content: str) -> str:
    """
    从短信内容中提取应用名称，并进行统一重命名。
    匹配 【新电途】 或 [小桔充电]
    """
    # 1. 正则提取括号内的应用名
    match = re.search(r'【(.*?)】|\[(.*?)]', content)
    app_name = match.group(1) or match.group(2) if match else "未知应用"

    # 2. 定义应用名称映射表（将原始名称映射为统一名称）
    app_name_mapping = {
        "滴滴充电": "小桔充电",
        # 以后如果有其他需要改名的，直接在这里添加即可
        # "滴滴出行": "滴滴"
        "滴滴出行": "小桔充电",
    }

    # 3. 返回映射后的名称，如果不在映射表中则返回原名
    return app_name_mapping.get(app_name, app_name)

def extract_app_phone(content):
    """
    匹配以 1 开头的 11 位连续数字
    """
    match = re.search(r'1[3-9]\d{9}', content)
    if match:
        return match.group()
    return "手机号"


def extract_code(content):
    """
    从短信内容中提取验证码。
    匹配 4-8 位数字验证码。
    """
    match = re.search(r'\b\d{4,8}\b', content)
    if match:
        return match.group(0)
    return ""


@sms_bp.route('/sms', methods=['POST'])
def receive_sms():
    try:
        data = request.get_json(force=True)
        logger.info(f"[Web接口] 收到data: [{data}]")
        phone_number = extract_app_phone(data.get('phone', ''))
        content = data.get('content', data.get('msg', ''))
        # timestamp = data.get('timestamp', '')

        if not phone_number or not content:
            return jsonify({"status": "error", "msg": "缺少手机号或内容"}), 400

        logger.info(f"[Web接口] 收到短信: [{phone_number}] {content}")

        # 1. 提取关键信息
        app_name = extract_app_name(content)
        code = extract_code(content)

        # 2. 直接调用封装好的方法保存验证码
        SmsConfigManager.save_verification_code(
            phone_number=phone_number,
            app_name=app_name,
            content=content,
            code=code
        )

        return jsonify({"status": "success", "app": app_name, "code": code}), 200

    except Exception as e:
        logger.info(f"[Web接口] 处理异常: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

