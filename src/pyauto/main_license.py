import sys

import pyauto.main as main
from pyauto.config.license_manager import LicenseManager
import tkinter as tk
from tkinter import messagebox

def main_license():
    license_manager = LicenseManager()
    flag,message=license_manager.verify_license()
    if not flag:
        try:
            root = tk.Tk()
            root.withdraw()
            root.update()    # 强制刷新事件循环，确保窗口初始化
            root.wm_attributes("-topmost", True) # 强制置顶

            messagebox.showwarning("⏰ 授权无效", message)
            root.destroy()

        except Exception:
            # 弹窗失败的降级方案
            print("\n⏰ 提示：该版本已过期！请获取最新版本。\n")
            input("按回车键退出...")
        sys.exit(0)
    main.main_logic()


if __name__ == "__main__":
    main_license()
