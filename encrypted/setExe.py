"""
文件名：setExe.py
实现oyarmor加密+ rsa 验签
功能：一键自动化打包脚本。
     1. 先运行 scan_imports.py 生成干净的 main_auto.py。
     2. 再运行 build_file_encrypted.py 进行加密和打包。
"""
import subprocess
import sys
import os
import argparse
from datetime import datetime, timedelta

def run_script(script_name, script_args=None):
    """
    运行指定的 Python 脚本
    """
    print(f"\n" + "="*50)
    print(f"⚙️ 正在执行: {script_name}")
    print("="*50)

    # 构建命令
    cmd = [sys.executable, script_name]
    if script_args:
        cmd.extend(script_args)

    try:
        # 使用 subprocess.run 确保脚本按顺序执行
        # check=True 会在脚本返回非0退出码时抛出异常
        subprocess.run(cmd, check=True)
        print(f"✅ {script_name} 执行成功！")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 错误：脚本 {script_name} 执行失败，退出码: {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\n❌ 发生未知错误: {e}")
        sys.exit(1)

def main():
    # 1. 设置命令行参数解析
    # parser = argparse.ArgumentParser(description="一键打包工具")
    # parser.add_argument('--expire', type=int, help='设置加密文件的过期时间（分钟）')
    # args = parser.parse_args()
    #
    # # 2. 计算过期时间
    # # 优先级：命令行参数 > 脚本内默认值
    # default_expire_minutes = 10
    # expire_minutes = args.expire if args.expire is not None else default_expire_minutes
    #
    # expire_time = (datetime.now() + timedelta(minutes=expire_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    # print(f"🕒 最终设置的过期时间为: {expire_time}")

    # 3. 第一步：运行 scan_imports.py
    # 这个脚本没有参数，直接运行即可
    run_script('scan_imports.py')

    # 4. 第二步：运行 build_file_encrypted.py
    # 将过期时间作为参数传递给它
    # run_script('build_file_encrypted.py', ['--expire', expire_time])
    run_script('build_file_encrypted.py')

    print("\n" + "="*50)
    # print(f"🕒 最终设置的过期时间为: {expire_time}")
    print("🎉 恭喜！所有步骤执行完毕！")
    print("="*50)

if __name__ == '__main__':
    main()