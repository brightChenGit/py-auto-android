# 文件名: remote_ocr_util.py
import requests
import base64
import io
from PIL import Image
import numpy as np
from typing import List, Dict, Any, Optional

class RemoteOCRUtil:
    """
    远程 OCR 客户端适配器。
    此类的接口设计与本地的 RapidOCRUtil 保持一致，以便无缝替换。
    """
    def __init__(self, server_url: str = "http://127.0.0.1:8889"):
        self.server_url = server_url.rstrip("/")

    def _image_to_base64(self, image) -> str:
        """将 PIL Image 或 numpy array 转换为 base64 字符串"""
        if not isinstance(image, Image.Image):
            # 如果是 numpy array，转换为 PIL Image
            image = Image.fromarray(image)
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def _post(self, endpoint: str, json_data: dict) -> Optional[Any]:
        """封装 POST 请求"""
        try:
            url = f"{self.server_url}{endpoint}"
            response = requests.post(url, json=json_data, timeout=15)
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get("status") == "success":
                    return resp_json.get("data")
                else:
                    print(f"[RemoteOCR] 服务错误: {resp_json.get('msg')}")
            else:
                print(f"[RemoteOCR] 请求失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"[RemoteOCR] 调用异常: {e}")
        return None

    # --- 以下方法签名与 RapidOCRUtil 完全一致 ---

    def ocr_full_screen(self, image) -> List:
        """对应 ocr_full_screen 方法"""
        img_str = self._image_to_base64(image)
        return self._post("/ocr/full", {"image_base64": img_str}) or []

    def ocr_crop(self, image, bounds: List[int]) -> List[str]:
        """对应 ocr_crop 方法"""
        img_str = self._image_to_base64(image)
        return self._post("/ocr/crop", {"image_base64": img_str, "bounds": bounds}) or []

    def ocr_full_screen_find(self, find_text, raw_results) -> List[Dict[str, Any]]:
        """
        对应 ocr_full_screen_find 方法。
        注意：此方法依赖于 ocr_full_screen 的输出结果。
        """
        return self._post("/ocr/find", {"find_text": find_text, "raw_results": raw_results}) or []

    def ocr_full_screen_common(self, find_text, screenshot) -> List[Dict[str, Any]]:
        """对应 ocr_full_screen_common 方法"""
        img_str = self._image_to_base64(screenshot)
        return self._post("/ocr/common", {"image_base64": img_str, "find_text": find_text}) or []