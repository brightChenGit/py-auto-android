"""
文件名: path_utils.py
功能: 处理 PyInstaller 打包后的资源文件路径问题
"""
import os
import sys

def model_resource_path(relative_path):
    """
    获取资源的绝对路径。
    用于 PyInstaller 打包后找到嵌入的资源文件。

    :param relative_path: 相对路径 (例如 'models/config.json')
    :return: 打包后或开发环境下的绝对路径
    """
    try:
        # PyInstaller 会创建一个临时文件夹，并把路径存放在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境下，base_path 是当前项目的根目录（相对于 main.py）
        # main.py 在 src/pyauto，models 在项目根目录，所以需要向上两级
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    return os.path.join(base_path, relative_path)