# main_auto.py
# 这是一个由 scan_imports.py 自动生成的干净入口文件
# 用于 PyInstaller 打包，以解决 PyArmor 加密后的依赖丢失问题

# --- 1. 导入所有第三方库 ---
# 这些 import 语句帮助 PyInstaller 扫描并打包所有依赖项
import PIL
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets
import abc
import asyncio
import atexit
import base64
import concurrent.futures
import cryptography.hazmat.primitives
import cryptography.hazmat.primitives.asymmetric
import cv2
import dataclasses
import datetime
import dbutils.pooled_db
import email.header
import email.mime.text
import flask
import functools
import gc
import hashlib
import io
import json
import logging
import multiprocessing
import numpy
import os
import pathlib
import psutil
import pymysql
import qasync
import random
import rapidocr
import re
import requests
import signal
import smtplib
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import tkinter
import traceback
import typing
import uiautomator2
import waitress
import webbrowser

# --- 2. 动态加载被 PyArmor 加密的核心业务模块 ---
import sys
import os
import tkinter as tk
from tkinter import messagebox
import importlib.util


def run_encrypted_main():
    
    if getattr(sys, "frozen", False):
        # 获取 PyInstaller 解压的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境下的路径
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist", "pyarmor_output")


    # 🔥 开始调试代码 🔥
    print("" + "="*40)
    print("🔍 开始验证打包文件结构...")
    print(f"当前临时目录 (base_path): {base_path}")

    # 1. 列出临时目录下的所有文件和文件夹
    print("📂 临时目录下的内容:")
    try:
        for item in os.listdir(base_path):
            print(f"  - {item}")
    except Exception as e:
        print(f"  读取目录失败: {e}")

    # 2. 检查 pyauto 文件夹是否存在
    pyauto_path = os.path.join(base_path, 'pyauto')
    print(f"📂 检查目标文件夹 'pyauto' 是否存在...")
    if os.path.exists(pyauto_path):
        print("✅ 成功找到 'pyauto' 文件夹！")

        # 3. 如果存在，列出 pyauto 文件夹下的内容
        print("📄 'pyauto' 文件夹内的内容:")
        try:
            for item in os.listdir(pyauto_path):
                print(f"  - {item}")
        except Exception as e:
            print(f"  读取目录失败: {e}")
    else:
        print("❌ 错误：未找到 'pyauto' 文件夹！")
        print("💡 这意味着 PyInstaller 的 --add-data 参数没有生效。")

    print("="*40 + "")
    # 🔥 关键修改：加密后的 main.py 现在位于 pyauto 子目录下
    encrypted_script = os.path.join(base_path, "pyauto", "main_encrypted.py")

    if not os.path.exists(encrypted_script):
        print(f"❌ 错误：未找到加密的核心模块 {encrypted_script}")
        sys.exit(1)

    # 将临时目录添加到 sys.path 的最前面，确保 pyauto 包可以被正常导入
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
    
    # 1. 正常加载并执行加密模块
    spec = importlib.util.spec_from_file_location("encrypted_main_module", encrypted_script)
    encrypted_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(encrypted_module)
        
 
    


if __name__ == "__main__":
    run_encrypted_main()
        