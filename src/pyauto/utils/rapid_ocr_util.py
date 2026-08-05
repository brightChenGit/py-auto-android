"""
文件名: rapid_ocr_util.py
功能: 封装 RapidOCR 的工具类 (单例模式)
备注:
    1. 请确保已安装 rapidocr_onnxruntime 库。
    2. 请在代码同级目录下放置模型文件夹。
    3. RapidOCR 模型需下载 ONNX 格式模型。
"""
import logging

import cv2
import os
import threading
from typing import List, Optional, Tuple, Any, Dict
import numpy as np
from pyauto.config.config_base import UnifiedConfigManager
import gc
# RapidOCR 相关导入
from rapidocr  import RapidOCR

# 假设你有一个 path_utils，如果没有，请替换为直接路径拼接
from pyauto.utils.path_utils import model_resource_path

_init_lock = threading.RLock() # 用于保护初始化过程

# ⭐️ 进程级全局变量：使用字典存储每个进程的引擎实例 {pid: engine}
_engines_cache: Dict[int, RapidOCR] = {}
_pid_lock = threading.Lock()  # 保护字典访问的锁

class RapidOCRUtil:
    """OCR 工具类 (进程级单例模式)"""
    _instance: Optional['RapidOCRUtil'] = None
    _engine: Optional[RapidOCR] = None
    _is_initialized = False # ⭐️ 新增：类级初始化标记

    def __new__(cls):
        if cls._instance is None:
            with _init_lock:
                # 双重检查，防止多线程竞争
                if cls._instance is None:
                    cls._instance = super(RapidOCRUtil, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # ⭐️ 关键修改：检查当前进程是否已初始化
        current_pid = os.getpid()

        # 快速检查：如果当前进程已有缓存，直接复用
        if current_pid in _engines_cache and _engines_cache[current_pid] is not None:
            self._engine = _engines_cache[current_pid]
            return

        # 需要初始化，加锁保护
        with _init_lock:
            # 双重检查：防止多线程竞争
            if current_pid in _engines_cache and _engines_cache[current_pid] is not None:
                self._engine = _engines_cache[current_pid]
                return

            # 执行初始化
            self._init_engine()

            # 保存到进程缓存
            _engines_cache[current_pid] = self._engine
            print(f"✅ [OCR] 进程 {current_pid} 初始化完成")


    def _init_engine(self):
        """初始化 OCR 引擎（适配 rapidocr v3+ 配置结构 + DirectML）"""
        try:
            pid = os.getpid()
            print(f"🔧 [OCR-{pid}] 正在初始化...")

            # 1. 计算模型路径
            # 注意：这里假设你的模型文件夹结构是：models/PP-OCRv4/det/xxx.onnx
            REAL_MODEL_DIR = model_resource_path("models")
            DET_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx")

            # 2. 识别模型 (Recognition)
            REC_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx")

            # 3. 方向分类模型 (Direction Classification)
            CLS_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx")

            # 检查模型文件是否存在
            det_model = DET_MODEL_PATH if os.path.exists(DET_MODEL_PATH) else None
            rec_model = REC_MODEL_PATH if os.path.exists(REC_MODEL_PATH) else None
            cls_model = CLS_MODEL_PATH if os.path.exists(CLS_MODEL_PATH) else None
            # 2. 构建参数字典 (Params)
            # 关键点：必须严格按照 config.yaml 中的层级书写键名
            params = {
                # --- 核心配置：指定模型根目录 ---
                # RapidOCR 会自动在这个目录下寻找 PP-OCRv4 等子文件夹
                # "Global.model_root_dir": REAL_MODEL_DIR,
                "Det.model_path": det_model,
                "Rec.model_path": rec_model,

                # --- 日志级别 (可选) ---
                "Global.log_level": "warning", # 减少日志输出

                # --- 检测与识别基础开关 (保持开启) ---
                "Global.use_det": True,
                "Global.use_rec": True,
                "Global.use_cls": False, # 如果不需要旋转分类，设为 False 提升速度

            }

            # --- 针对 DirectML 的特殊配置 ---
            # 根据你的 config.yaml 结构，我们需要手动指定 ONNX Runtime 的执行提供者
            # 注意：在旧版本 DirectML 中，通常需要强制关闭 CUDA
            params.update({
                "EngineConfig.onnxruntime.enable_cpu_mem_arena": False, # 降低内存占用
                "EngineConfig.onnxruntime.use_cuda": UnifiedConfigManager.get_config().get("ocr",{}).get("use_cuda", False),  # 强制关闭 CUDA
                "EngineConfig.onnxruntime.use_dml": UnifiedConfigManager.get_config().get("ocr",{}).get("use_dml", False),    # 尝试开启 DML (如果库版本支持)
                # 如果上面的 use_dml 不生效，可能需要通过环境变量或代码层面指定 providers
            })

            # 3. 初始化引擎
            # 注意：这里传入的是 params 字典，而不是直接传路径
            engine = RapidOCR(params=params)

            print(f"✅ [OCR-{pid}] 初始化成功 (模型目录: {REAL_MODEL_DIR})")
            self._engine = engine

        except Exception as e:
            print(f"❌ [OCR-{pid}] 初始化失败: {e}")
            import traceback; traceback.print_exc()
            raise




    def ocr_crop(self, image, bounds: List[int]) -> List[str]:
        """
        功能: 对图像的指定区域进行 OCR 识别。
        :param image: 图像对象 (numpy array)
        :param bounds: 区域坐标 [x1, y1, x2, y2]
        :return: 包含识别出的文本的列表
        """
        try:
            # 1. 确保输入是 numpy array
            if not isinstance(image, np.ndarray):
                image = np.array(image)

            # 2. 裁剪区域
            crop_img = image[bounds[1]:bounds[3], bounds[0]:bounds[2]]

            output = self._engine(crop_img)

            texts = []
            # 新版 output.results 是 List[Dict] 或 List[List]
            # if output.results:
            #     for line in output.results:
            #         # 兼容两种可能的结构：[box, text, score] 或 Dict
            #         if isinstance(line, (list, tuple)):
            #             text = line[1] # 通常索引 1 是文本
            #         elif isinstance(line, dict):
            #             text = line.get("text", "")
            #         texts.append(text)
            return texts

        except Exception as e:
            print(f"区域识别失败: {e}")
            return []


    def ocr_full_screen(self, image) -> List:
        """
        功能: 对全屏图像进行 OCR 识别，返回结构化数据。
        适配 RapidOCR 最新返回格式 (包含 txts, boxes, scores 属性)。
        """
        try:
            # 1. 类型转换
            if not isinstance(image, np.ndarray):
                image = np.array(image)

            # 2. 执行预测
            output = self._engine(image)
            # print(f"Raw Output: {output}") # 调试用：打印原始输出

            formatted_result = []

            # --- 关键修复点 ---
            # 根据日志 [1]，直接使用 output.txts, output.boxes, output.scores
            # 并且需要通过索引 i 来遍历，而不是 for line in output.results

            texts = output.txts
            boxes = output.boxes
            scores = output.scores

            # 确保数据存在且长度一致
            if texts and len(texts) > 0 and len(texts) == len(boxes):
                for i in range(len(texts)):
                    try:
                        # --- 处理坐标 Box ---
                        box_array = boxes[i]

                        # 转换为标准 Python 列表
                        if hasattr(box_array, 'tolist'):
                            box = box_array.tolist()
                        else:
                            box = [[float(p[0]), float(p[1])] for p in box_array]

                        # --- 处理文本和置信度 ---
                        text = texts[i]
                        score = scores[i] if i < len(scores) else 0.0

                        formatted_result.append([box, (text, score)])

                    except Exception as e:
                        # 捕获单行解析错误，防止整个 OCR 崩溃
                        print(f"解析第 {i} 行 OCR 结果失败: {e}")
                        continue
            return formatted_result
        except Exception as e:
            print(f"全屏 OCR 失败: {e}")
            import traceback; traceback.print_exc()
            return []
        finally:
            # ⭐️ 核心“止血”代码：无论识别成功还是报错，都会执行这一步
            # 强制触发 Python 的垃圾回收机制，释放未被自动清理的内存
            gc.collect()

    def ocr_full_screen_fast(self, screenshot, short_side_len: int = 450) -> List[Dict[str, Any]]:
        """
        执行全屏 OCR，自动缩放图片以提升速度，并还原坐标。
        (此方法保留了原代码逻辑，但 RapidOCR 本身已经很快，通常不需要缩放)
        """
        # 如果传入的是 PIL Image，获取尺寸
        if hasattr(screenshot, 'size'):
            original_width, original_height = screenshot.size
        else: # numpy array
            h, w = screenshot.shape[:2]
            original_width, original_height = w, h

        print(f"图片: c -> {original_width}x{original_height}")

        # --- 1. 图片预处理（缩放） ---
        current_short_side = min(original_width, original_height)
        scale_ratio = 1.0
        img_to_ocr = screenshot

        if current_short_side > short_side_len:
            scale_ratio = short_side_len / current_short_side
            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)

            # 转为 PIL 进行高质量缩放，或者直接用 cv2
            if hasattr(screenshot, 'resize'):
                img_to_ocr = screenshot.resize((new_width, new_height))
            else:
                # 如果是 numpy array
                img_to_ocr = cv2.resize(screenshot, (new_width, new_height), interpolation=cv2.INTER_AREA)

            print(f"图片已缩放: c -> {new_width}x{new_height}")

        # --- 2. 执行 OCR ---
        raw_results = self.ocr_full_screen(img_to_ocr)

        # --- 3. 解析字典并还原坐标 ---
        final_results = []

        # raw_results 格式: [ [box, (text, score)] ]
        for item in raw_results:
            box = item[0] # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = item[1][0]
            score = item[1][1]

            # RapidOCR 返回的 box 通常是 4 个点的坐标
            # 计算中心点 (使用左上和右下)
            x_coords = [point[0] for point in box]
            y_coords = [point[1] for point in box]
            center_x = np.mean(x_coords) / scale_ratio
            center_y = np.mean(y_coords) / scale_ratio

            # 还原完整 4 点坐标
            real_box = [[p[0]/scale_ratio, p[1]/scale_ratio] for p in box]

            final_results.append({
                "text": text,
                "point": (int(center_x), int(center_y)),
                "box": real_box,
                "confidence": score
            })

        return final_results

    def ocr_full_screen_find(self,find_text,raw_results)-> List[Dict[str, Any]]:
        """
        简化版全屏 OCR，只查找包含特定文本的内容。
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
                # 如果只需要第一个匹配项，可以在这里 break
                # break

        return final_results



    def ocr_full_screen_common(self, find_text, screenshot) -> List[Dict[str, Any]]:
        """
        简化版全屏 OCR，只查找包含特定文本的内容。
        """
        raw_results = self.ocr_full_screen(screenshot)
        return self.ocr_full_screen_find(find_text, raw_results)

    @staticmethod
    def cleanup():
        """
        清理当前进程的 OCR 引擎（可选，用于释放内存）
        通常在进程退出时自动清理，无需手动调用
        """
        current_pid = os.getpid()
        if current_pid in _engines_cache and _engines_cache[current_pid] is not None:
            print(f"🧹 [OCR-{current_pid}] 清理 OCR 引擎...")
            del _engines_cache[current_pid]
            RapidOCRUtil._instance = None
            RapidOCRUtil._is_initialized = False
            print(f"✅ [OCR-{current_pid}] OCR 引擎已清理")


# =================================================
# 🔧 快速测试入口
# =================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("Test")

    # 测试图像路径或创建白底图
    # test_image = np.ones((720, 1280, 3), dtype=np.uint8) * 255
    test_image_np = np.ones((200, 400, 3), dtype=np.uint8) * 255
    # 如果有测试图片，取消注释下面这行
    # test_image = cv2.imread("img_1.png")


    try:
        cv2.putText(test_image_np, 'Sample Text OCR Test', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        logger.info("✅ 已生成带文字的测试图片 (NumPy Array)")
    except:
        logger.info("⚠️ OpenCV 不可用，使用纯色图测试 (可能无文字)")
    try:
        test_image =test_image_np
        ocr = RapidOCRUtil()
        gray = cv2.cvtColor(test_image_np, cv2.COLOR_BGR2GRAY)
        # 测试全屏 (如果上面创建了 test_image)
        full_result = ocr.ocr_full_screen(test_image)
        logger.info(f"全屏测试完成，识别到 {len(full_result)} 个元素")

        # full_result = ocr.ocr_full_screen(test_image)
        # logger.info(f"全屏测试完成，识别到 {full_result} ")

        find_text=ocr.ocr_full_screen_common(find_text="地图",screenshot=test_image)
        logger.info(f"全屏测试完成，识别到 {find_text} ")

        find_text=ocr.ocr_full_screen_common(find_text="地图",screenshot=test_image)
        logger.info(f"第二次全屏测试完成，识别到 {find_text} ")
        # find_text=ocr.ocr_full_screen_common(find_text="地图",screenshot=gray)
        # logger.info(f"全屏测试gray完成，识别到 {find_text} ")
        # 测试裁剪
        crop_result = ocr.ocr_crop(test_image, [100, 100, 200, 200])
        logger.info(f"裁剪测试结果: {crop_result}")

    except Exception as e:
        logger.info(f"测试运行出错: {e}")