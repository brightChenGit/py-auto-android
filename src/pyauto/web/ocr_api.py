# 文件名: ocr_api.py
from flask import Blueprint, request, jsonify
# 1. 修改导入：为 waitress 的 serve 函数起一个别名
from waitress import serve
import base64
import io
import numpy as np
from PIL import Image
import gc # 用于内存回收
import threading # 新增导入

# 2. 导入新的服务端工具类
from pyauto.utils.server_ocr_util import ServerOCRUtil

# 1. 创建一个名为 'ocr_bp' 的蓝图
ocr_bp = Blueprint('ocr', __name__)

def _decode_image(image_base64):
    """辅助函数：将 base64 字符串解码为 numpy array"""
    image_bytes = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(image_bytes))
    return np.array(image)

@ocr_bp.route('/ocr/full', methods=['POST'])
def ocr_full():
    """对应 ocr_full_screen 方法"""
    try:
        data = request.get_json(force=True)
        image_np = _decode_image(data.get('image_base64'))
        result = ServerOCRUtil.ocr_full_screen(image_np)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500
    finally:
        # ⭐️ 关键：在服务端执行垃圾回收
        gc.collect()

@ocr_bp.route('/ocr/crop', methods=['POST'])
def ocr_crop():
    """对应 ocr_crop 方法"""
    try:
        data = request.get_json(force=True)
        image_np = _decode_image(data.get('image_base64'))
        bounds = data.get('bounds')
        if not bounds:
            return jsonify({"status": "error", "msg": "缺少 bounds 参数"}), 400
        result = ServerOCRUtil.ocr_crop(image_np, bounds)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500
    finally:
        # ⭐️ 关键：在服务端执行垃圾回收
        gc.collect()

@ocr_bp.route('/ocr/find', methods=['POST'])
def ocr_find():
    """对应 ocr_full_screen_find 方法"""
    try:
        data = request.get_json(force=True)
        find_text = data.get('find_text')
        raw_results = data.get('raw_results')
        if not find_text or not raw_results:
            return jsonify({"status": "error", "msg": "缺少 find_text 或 raw_results 参数"}), 400
        result = ServerOCRUtil.ocr_full_screen_find(find_text, raw_results)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500
    # 注意：此接口不直接调用 OCR 引擎，所以不需要 gc.collect()

@ocr_bp.route('/ocr/common', methods=['POST'])
def ocr_common():
    """对应 ocr_full_screen_common 方法"""
    try:
        data = request.get_json(force=True)
        image_np = _decode_image(data.get('image_base64'))
        find_text = data.get('find_text')
        if not find_text:
            return jsonify({"status": "error", "msg": "缺少 find_text 参数"}), 400
        result = ServerOCRUtil.ocr_full_screen_common(find_text, image_np)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500
    finally:
        # ⭐️ 关键：在服务端执行垃圾回收
        gc.collect()
