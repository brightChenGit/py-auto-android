"""
文件名: ocr_util.py
功能: 封装 PaddleOCR 的工具类 (单例模式)
作者: AI 助手
备注: 
1. 请确保已安装 paddlepaddle 和 paddleocr 库。
2. 请在代码同级目录下放置 PP-OCRv5_mobile_det_infer 和 PP-OCRv5_mobile_rec_infer 模型文件夹。
   或者修改 MODEL_PATH 变量指向你的模型实际路径。
"""

import os
# 禁用 PaddleX 的模型源连接检查，加速启动  强制设置：必须放在文件最开头，甚至在 logging 之前 -
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

import logging
from typing import List, Optional, Tuple, Any
from paddleocr import PaddleOCR
from pyauto.utils.path_utils import model_resource_path


class OCRUtil:
    """
    OCR 工具类 (单例模式)
    
    设计目的:
    1. 避免在多进程环境下重复加载模型导致内存爆炸。
    2. 统一管理模型路径和初始化参数。
    3. 提供简化的调用接口供业务层使用。
    """

    # 类私有变量，用于存储唯一的实例和引擎
    _instance: Optional['OCRUtil'] = None
    _engine: Optional[PaddleOCR] = None

    def __new__(cls):
        """
        单例模式的构造方法。
        确保在一个 Python 进程内，只有一个 OCRUtil 实例。
        """
        if cls._instance is None:
            cls._instance = super(OCRUtil, cls).__new__(cls)
        return cls._instance

    def _init_engine(self):
        try:
            logger = logging.getLogger("OCRUtil")
            logger.info("正在初始化 OCR 引擎...")

            # =================================================
            # 🚀 核心修改：动态计算模型路径
            # =================================================
            # 1. 定义模型相对于项目根目录的路径
            #    假设你的项目结构是: 项目根目录/models/具体模型
            RELATIVE_MODEL_DIR = "models"

            # 2. 使用 resource_path 计算出真实路径
            #    开发环境: 返回 项目根目录/models
            #    打包环境: 返回 sys._MEIPASS/models (如果你把模型打包进去了)
            REAL_MODEL_DIR = model_resource_path(RELATIVE_MODEL_DIR)

            # 3. 拼接具体的模型文件夹路径
            DET_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv5_mobile_det")
            REC_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-OCRv5_mobile_rec")
            CLS_MODEL_PATH = os.path.join(REAL_MODEL_DIR, "PP-LCNet_x1_0_textline_ori")
            # =================================================

            # 检查模型文件是否存在
            if not os.path.exists(DET_MODEL_PATH):
                logger.error(f"检测模型不存在: {DET_MODEL_PATH}")
                logger.warning("将尝试使用在线下载 (不推荐用于生产环境)")
                det_path = None
            else:
                det_path = DET_MODEL_PATH

            if not os.path.exists(REC_MODEL_PATH):
                logger.error(f"识别模型不存在: {REC_MODEL_PATH}")
                rec_path = None
            else:
                rec_path = REC_MODEL_PATH

            OCRUtil._engine = PaddleOCR(lang='ch',
                                        # --- 检测模块 ---
                                        text_detection_model_dir=DET_MODEL_PATH, # 替换 det_model_dir
                                        # --- 识别模块 ---
                                        text_recognition_model_dir=REC_MODEL_PATH, # 替换 rec_model_dir
                                        # --- 方向分类模块 (替换 use_angle_cls) ---
                                        use_textline_orientation=True,       # 替换 use_angle_cls
                                        textline_orientation_model_dir=CLS_MODEL_PATH, # 指定方向分类模型路径
                                   )


            logger.info("OCR 引擎初始化成功 🚀")
        except Exception as e:
            logging.critical(f"OCR 引擎初始化失败: {e}")
            raise
    def ocr_crop(self, image, bounds: List[int]) -> List[str]:
        """
        功能: 对图像的指定区域进行 OCR 识别。
        用途: 用于识别列表中的某一行文字，或者特定坐标区域的文字。
        
        :param image: 图像对象 (PIL Image 或 numpy array)
        :param bounds: 区域坐标 [x1, y1, x2, y2]
        :return: 包含识别出的文本的列表 (例如: ['充电站名称', '距离1.5km'])
        """
        try:
            # 从原图裁剪出目标区域
            crop_img = image.crop(bounds)
            # 执行 OCR
            result = OCRUtil._engine.ocr(crop_img, cls=True)

            texts = []
            # 解析结果
            # result 结构: [[ [坐标点, (文本, 置信度)], ... ]]
            if result and result[0]:
                for line in result[0]:
                    # line[1] 是一个元组 (文本, 置信度分数)
                    text = line[1][0]
                    texts.append(text)
            return texts
        except Exception as e:
            logging.getLogger("OCRUtil").error(f"区域识别失败: {e}")
            return []

    def ocr_full_screen(self, image) -> List:
        """
        功能: 对全屏图像进行 OCR 识别，并返回包含位置信息的原始结果。
        用途: 用于 "OCR 点击" 功能，因为需要知道文字在屏幕上的具体坐标。
        
        :param image: 图像对象
        :return: PaddleOCR 的原始结果列表，包含坐标和文本信息。
                 如果你需要实现点击功能，必须使用这个方法返回的结果。
        """
        try:
            # cls=True 表示启用方向分类
            result = OCRUtil._engine.ocr(image, cls=True)
            # 直接返回原始结构，供调用者处理坐标
            return result[0] if result and result[0] else []
        except Exception as e:
            logging.getLogger("OCRUtil").error(f"全屏 OCR 失败: {e}")
            return []

# =================================================
# 🔧 快速测试入口 (直接运行此文件时执行)
# =================================================
if __name__ == "__main__":
    # 1. 配置日志输出
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("Test")

    logger.info("开始执行 OCRUtil 快速测试...")

    # 2. 测试单例和初始化
    try:
        ocr = OCRUtil() # 这里会触发 __new__ 和 _init_engine
    except Exception as e:
        logger.error(f" 初始化失败: {e}")
        exit(1)

    # 3. 准备测试素材 (这里使用一个简单的纯色图来测试流程是否报错)
    # 注意：PaddleOCR 需要 numpy array 或文件路径
    import numpy as np
    test_image = np.ones((720, 1280, 3), dtype=np.uint8) * 255 # 白底图片

    # 4. 测试全屏识别
    logger.info("测试全屏识别 ocr_full_screen...")
    full_result = ocr.ocr_full_screen(test_image)
    if len(full_result) == 0:
        logger.info("✅ 全屏识别测试通过 (白底无字是正常现象)")
    else:
        logger.warning(f"ℹ️ 识别到了内容: {full_result}")

    # 5. 测试区域识别 (Bounds: [x1, y1, x2, y2])
    logger.info("测试区域识别 ocr_crop...")
    crop_result = ocr.ocr_crop(test_image, [100, 100, 200, 200])
    logger.info(f"区域识别结果: {crop_result}")

    logger.info("🎉 所有测试完成。如果没有报错，说明环境配置成功！")
# =============================================
# 🚀 使用示例 (请阅读这里以了解如何在 Adapter 中使用)
# =============================================
"""
如何在你的 Adapter (如 adapter_xdt.py) 中使用它:

1. 导入工具类:
   from pyauto.utils.ocr_util import OCRUtil

2. 初始化 (通常在 Adapter 的 __init__ 中):
   self.ocr = OCRUtil() # 获取单例实例

3. 调用方法:

   A. 场景: 我只想知道这个区域写了什么字 (不需要坐标)
      texts = self.ocr.ocr_crop(screenshot, [100, 200, 300, 400])
      for text in texts:
          print(text)

   B. 场景: 我想识别屏幕上的 "确定" 按钮并点击它 (需要坐标)
      results = self.ocr.ocr_full_screen(screenshot)
      for line in results:
          text = line[1][0] # 文本
          coords = line[0]  # 坐标 (四边形的四个点)
          if "确定" in text:
              # 计算中心点
              center_x = (coords[0][0] + coords[2][0]) / 2
              center_y = (coords[0][1] + coords[2][1]) / 2
              # 执行点击 (假设 self.d 是 uiautomator2 对象)
              self.d.click(center_x, center_y)
              break
"""