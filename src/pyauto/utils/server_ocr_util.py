# 文件名: server_ocr_util.py
import gc
import logging
import os
from typing import List, Optional, Any, Dict
import numpy as np
from pyauto.config.config_base import UnifiedConfigManager
from pyauto.utils.path_utils import model_resource_path
# RapidOCR 相关导入
from rapidocr import RapidOCR

class ServerOCRUtil:
    """
    服务端专用的 OCR 工具类。
    简化了进程级单例逻辑，只负责在应用启动时初始化一次引擎。
    """
    _engine: Optional[RapidOCR] = None

    @classmethod
    def get_engine(cls) -> RapidOCR:
        """获取单例的 OCR 引擎实例，如果未初始化则先进行初始化"""
        if cls._engine is None:
            cls._init_engine()
        return cls._engine

    @classmethod
    def _init_engine(cls):
        """初始化 OCR 引擎"""
        try:
            print(f"🔧 [OCR-Server] 正在初始化 OCR 引擎...")

            # 1. 计算模型路径 (逻辑与原 rapid_ocr_util.py 保持一致)
            REAL_MODEL_DIR = model_resource_path("models")
            DET_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx")
            REC_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx")
            CLS_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx")

            det_model = DET_MODEL_PATH if os.path.exists(DET_MODEL_PATH) else None
            rec_model = REC_MODEL_PATH if os.path.exists(REC_MODEL_PATH) else None
            cls_model = CLS_MODEL_PATH if os.path.exists(CLS_MODEL_PATH) else None

            # 2. 构建参数字典
            params = {
                "Det.model_path": det_model,
                "Rec.model_path": rec_model,
                "Global.log_level": "warning",
                "Global.use_det": True,
                "Global.use_rec": True,
                "Global.use_cls": False,
                "EngineConfig.onnxruntime.enable_cpu_mem_arena": True,
                "EngineConfig.onnxruntime.use_cuda": UnifiedConfigManager.get_config().get("ocr",{}).get("use_cuda", False),
                "EngineConfig.onnxruntime.use_dml": UnifiedConfigManager.get_config().get("ocr",{}).get("use_dml", False),
            }

            # 3. 初始化引擎
            cls._engine = RapidOCR(params=params)
            print(f"✅ [OCR-Server] 引擎初始化成功")

        except Exception as e:
            print(f"❌ [OCR-Server] 引擎初始化失败: {e}")
            import traceback; traceback.print_exc()
            raise

    # --- 以下方法将原 RapidOCRUtil 中的业务逻辑剥离出来，变为纯函数 ---

    @staticmethod
    def ocr_full_screen(image) -> List:
        """全屏 OCR 识别"""
        try:
            if not isinstance(image, np.ndarray):
                image = np.array(image)

            engine = ServerOCRUtil.get_engine()
            output = engine(image)

            formatted_result = []
            # 兼容 RapidOCR 的返回格式
            if hasattr(output, 'txts') and output.txts:
                for i in range(len(output.txts)):
                    try:
                        box_array = output.boxes[i]
                        box = box_array.tolist() if hasattr(box_array, 'tolist') else [[float(p[0]), float(p[1])] for p in box_array]
                        text = output.txts[i]
                        score = output.scores[i] if i < len(output.scores) else 0.0
                        formatted_result.append([box, (text, score)])
                    except Exception as e:
                        print(f"解析第 {i} 行 OCR 结果失败: {e}")
                        continue



            # del output
            # gc.collect()
            return formatted_result
        except Exception as e:
            print(f"全屏 OCR 失败: {e}")
            return []

    @staticmethod
    def ocr_crop(image, bounds: List[int]) -> List[str]:
        """区域 OCR 识别"""
        try:
            if not isinstance(image, np.ndarray):
                image = np.array(image)
            crop_img = image[bounds[1]:bounds[3], bounds[0]:bounds[2]]

            engine = ServerOCRUtil.get_engine()
            output = engine(crop_img)

            texts = []
            if hasattr(output, 'txts') and output.txts:
                texts = output.txts

            # del output
            # gc.collect()
            return texts
        except Exception as e:
            print(f"区域识别失败: {e}")
            return []

    @staticmethod
    def ocr_full_screen_find(find_text, raw_results) -> List[Dict[str, Any]]:
        """
        简化版全屏 OCR，只查找包含特定文本的内容。
        这是一个纯逻辑函数，不直接调用引擎。
        """
        final_results = []
        for item in raw_results:
            box = item[0]
            text_info = item[1] # (text, score)
            text = text_info[0]
            score = text_info[1]
            if find_text in text:
                # 计算中心点
                x_coords = [point[0] for point in box]
                y_coords = [point[1] for point in box]
                center_x = np.mean(x_coords)
                center_y = np.mean(y_coords)
                final_results.append({
                    "text": text,
                    "point": (int(center_x), int(center_y)),
                    "confidence": score
                })
        return final_results

    @staticmethod
    def ocr_full_screen_common(find_text, screenshot) -> List[Dict[str, Any]]:
        """
        简化版全屏 OCR，只查找包含特定文本的内容。
        这是 ocr_full_screen 和 ocr_full_screen_find 的组合。
        """
        raw_results = ServerOCRUtil.ocr_full_screen(screenshot)
        return ServerOCRUtil.ocr_full_screen_find(find_text, raw_results)