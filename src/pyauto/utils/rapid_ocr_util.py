"""
文件名: rapid_ocr_util.py
功能: 封装 RapidOCR 的工具类 (单例模式)
作者: AI 助手
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
import onnxruntime as ort

# RapidOCR 相关导入
from rapidocr_onnxruntime import RapidOCR

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
        """初始化 OCR 引擎（每个进程只执行一次）"""
        try:
            pid = os.getpid()
            print(f"🔧 [OCR-{pid}] 开始初始化 OCR 引擎...")
            # 1. 开启 ONNX 的图优化 (关键!)
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            # 2. 获取当前环境支持的所有加速提供者
            available_providers = ort.get_available_providers()
            print(f"🔍 [OCR] ONNX Runtime 可用设备: {available_providers}")

            # 3. 定义优先级策略
            # 逻辑：如果有 CUDA (NVIDIA) 优先用 CUDA；否则如果有 DML (Intel/AMD) 用 DML；最后回退到 CPU
            target_providers = ['CPUExecutionProvider'] # 默认回退到 CPU

            if 'CUDAExecutionProvider' in available_providers:
                target_providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                print("⚡ [OCR] 检测到 NVIDIA GPU，已启用 CUDA 加速")
            elif 'DmlExecutionProvider' in available_providers:
                target_providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
                print("⚡ [OCR] 检测到 DirectML 设备 (Intel/AMD)，已启用 DirectML 加速")
            elif 'OpenVINOExecutionProvider' in available_providers:
                # 额外赠送：如果你的 Intel 显卡装了 OpenVINO 插件，这个通常比 DirectML 更快
                target_providers = ['OpenVINOExecutionProvider', 'CPUExecutionProvider']
                print("⚡ [OCR] 检测到 OpenVINO 设备，已启用 OpenVINO 加速")
            else:
                print("⚠️ [OCR] 未检测到 GPU 加速库，使用 CPU 模式 (速度较慢)")
            # =================================================
            # 🚀 核心修改：动态计算模型路径
            # =================================================
            RELATIVE_MODEL_DIR = "models"  # 你的模型文件夹名
            REAL_MODEL_DIR = model_resource_path(RELATIVE_MODEL_DIR)

            # 1. 检测模型 (Detection)
            # DET_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv5/det/ch_PP-OCRv5_det_mobile.onnx")
            DET_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx")
            # DET_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/det/ch_PP-OCRv4_det_server.onnx")
            # DET_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv5/det/ch_PP-OCRv5_det_server.onnx")

            # 2. 识别模型 (Recognition)
            # REC_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv5/rec/ch_PP-OCRv5_rec_mobile.onnx")
            REC_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx")
            # REC_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/rec/ch_PP-OCRv4_rec_server.onnx")
            # REC_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv5/rec/ch_PP-OCRv5_rec_server.onnx")

            # 3. 方向分类模型 (Direction Classification)
            # CLS_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv5/cls/ch_PP-LCNet_x0_25_textline_ori_cls_mobile.onnx")
            CLS_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx")

            # 检查模型文件是否存在
            det_model = DET_MODEL_PATH if os.path.exists(DET_MODEL_PATH) else None
            rec_model = REC_MODEL_PATH if os.path.exists(REC_MODEL_PATH) else None
            cls_model = CLS_MODEL_PATH if os.path.exists(CLS_MODEL_PATH) else None

            # =================================================
            # 🔑 初始化 RapidOCR
            # =================================================
            # 注意: RapidOCR 使用 ONNXRuntime，无需设置 MKLDNN
            engine = RapidOCR(
                # 模型路径配置
                det_model_path=det_model,
                rec_model_path=rec_model,
                # cls_model_path=cls_model,
                cls_model_path=None,

                # 功能开关 (对应 PaddleOCR 的 use_*)
                use_det=True,      # 开启检测
                use_rec=True,      # 开启识别
                use_cls=False,      # 开启方向分类


                # 性能与设备配置
                # sess_options=sess_options, # 应用上面的图优化
                providers=target_providers,
                # cpu_num_threads=4,
                # det_db_box_thresh=0.3,   # 检测阈值，降低可减少噪点框
                # det_db_unclip_ratio=1.5, # 控制框的紧凑程度
                # max_batch_size=1,        # 确保是 1 (单张推理)

                # 线程数 (对应 PaddleOCR 的 cpu_threads，但 RapidOCR 主要由 ONNX 控制)
                # 可以通过环境变量控制，或者在 ONNX 选项中设置
                # det_limit_side_len=960, # 预测时图像长边限制，影响速度
                # rec_image_shape="3, 32, 100" # 识别模型输入形状
            )

            print(f"✅ [OCR-{pid}] RapidOCR 引擎初始化成功 🚀")
            
            # ⭐️ 保存引擎到实例
            self._engine = engine

            # 模型预热 (Warm-up)
            # dummy_img = np.ones((64, 64, 3), dtype=np.uint8) * 255
            # try:
            #     self._engine(dummy_img)
            #     print("模型预热完成 🔥")
            # except:
            #     pass

        except Exception as e:
            print(f"OCR 引擎初始化失败: {e}")
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

            # 3. 执行 OCR
            # RapidOCR 返回: [[box, text, score], ...]
            result, _ = self._engine(crop_img)

            texts = []
            if result is not None:
                for line in result:
                    # line[1] 是 text
                    texts.append(line[1])
            return texts

        except Exception as e:
            print(f"区域识别失败: {e}")
            return []

    def ocr_full_screen(self, image) -> List:
        """
        功能: 对全屏图像进行 OCR 识别，返回原始结果。
        :param image: 图像对象 (numpy array)
        :return: 原始结果列表 (包含坐标和文本)
        """
        try:
            # 1. 类型转换
            if not isinstance(image, np.ndarray):
                image = np.array(image)

            # 如果是 cv2 格式处理，建议转为 BGR (RapidOCR 内部通常处理 BGR 或 RGB 都可以，但 cv2 读取是 BGR)
            # img_cv = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            # 2. 执行预测
            result, elapse = self._engine(image)

            # 3. 返回结构化数据
            # 将 RapidOCR 的格式转换为类似 PaddleOCR 的结构以便兼容
            # RapidOCR: [ [[x1,y1],...], "文本", 0.99 ]
            # 转换为: [ [坐标], ("文本", 置信度) ]
            formatted_result = []
            if result is not None:
                for line in result:
                    box = line[0]  # 坐标框
                    text = line[1] # 文本
                    score = line[2] # 置信度
                    formatted_result.append([box, (text, score)])

            return formatted_result

        except Exception as e:
            print(f"全屏 OCR 失败: {e}")
            return []

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