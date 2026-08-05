# encrypted/build_file_encrypted.py
import os
import sys
import shutil
import subprocess
from datetime import timedelta, datetime
import argparse

def run_command(command, shell=True):
    """运行系统命令并实时打印输出"""
    print(f"⚙️ 正在执行: {command}")
    process = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True, encoding='utf-8', errors='replace')
    for line in process.stdout:
        print(line, end='')
    process.wait()
    if process.returncode != 0:
        raise Exception(f"命令执行失败，返回码: {process.returncode}")

def build():
    # --- 新增：解析命令行参数 ---
    parser = argparse.ArgumentParser()
    parser.add_argument('--expire', type=str, help='设置过期时间，格式为 "YYYY-MM-DD HH:MM:SS"')
    args, unknown = parser.parse_known_args() # 使用 parse_known_args 避免与 PyInstaller 参数冲突

    print("🚀 开始构建项目 (PyArmor + PyInstaller)...")

    # 1. 获取项目根目录 (从 encrypted 目录向上一级)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ENCRYPTED_DIR = os.path.dirname(os.path.abspath(__file__))

    # 2. 定义核心业务代码目录 (将被整体加密)
    CORE_PACKAGE = os.path.join(PROJECT_ROOT, 'src', 'pyauto')
    SOURCE_LICENSE=os.path.join(PROJECT_ROOT, 'src', 'pyauto', 'config','license.dat')
    # 3. 定义需要打包的资源文件 (源路径, 目标路径)
    DATA_LIST = [
        (os.path.join(PROJECT_ROOT, 'src', 'pyauto', 'bin'), 'bin'),
        (os.path.join(PROJECT_ROOT, 'models'), 'models'),
    ]

    # 4. 检查资源目录是否存在
    print("🔍 正在检查资源目录...")
    for src, dest in DATA_LIST:
        if not os.path.exists(src):
            print(f"❌ 错误：资源目录未找到 -> {src}")
            sys.exit(1)
    print("✅ 所有资源检查通过")

    # 5. 第一步：使用 PyArmor 递归加密整个 pyauto 包
    print("\n🔒 正在使用 PyArmor 加密核心代码...")
    dist_dir = os.path.join(PROJECT_ROOT, 'dist')
    pyarmor_dist = os.path.join(dist_dir, 'pyarmor_output')

    if os.path.exists(pyarmor_dist):
        shutil.rmtree(pyarmor_dist)



    if args.expire:
        expire_time = args.expire
        print(f"⏳ 使用传入的过期时间: {expire_time}")
    else:
        # 如果没有传入，则使用默认的10分钟
        expire_time = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        print(f"⏳ 使用默认的过期时间: {expire_time}")

    # 核心修改：指定整个 src/pyauto 目录作为加密目标
    # pyarmor_cmd = f'pyarmor gen -O "{pyarmor_dist}" --recursive -e "{expire_time}" "{CORE_PACKAGE}"'
    # --assert-import：会检查每一个 import 语句，确保被导入的模块是加密过的，防止 license_manager.py 等核心模块被替换为明文脚本。
    # --private：会启用私有模式，隐藏函数名称并防止加密后的脚本被外部未加密的普通脚本导入。
    # print(f"{pyarmor_dist}")
    pyarmor_cmd = f'pyarmor gen -O "{pyarmor_dist}" --recursive "{CORE_PACKAGE}"'
    pyarmor_cmd_assert1 = f'pyarmor cfg -p pyauto.config.license_manager assert_import = 1'
    # pyarmor_cmd_assert2 = f'pyarmor cfg -p pyauto.main_license assert_import = 1'
    # pyarmor_cmd_assert3 = f'pyarmor cfg -p pyauto.main_encrypted assert_import =0'
    pyarmor_cmd_private1 = f'pyarmor cfg -p pyauto.config.license_manager private = 1'
    # pyarmor_cmd_private2 = f'pyarmor cfg -p pyauto.main_license private = 1'
    # pyarmor_cmd_private3 = f'pyarmor cfg -p pyauto.main_encrypted private = 1'

    try:
        run_command(pyarmor_cmd)
        run_command(pyarmor_cmd_assert1)
        # run_command(pyarmor_cmd_assert2)
        # run_command(pyarmor_cmd_assert3)
        run_command(pyarmor_cmd_private1)
        # run_command(pyarmor_cmd_private2)
        # run_command(pyarmor_cmd_private3)
        print("✅ PyArmor 加密完成")
    except Exception as e:
        print(f"❌ PyArmor 加密失败: {e}")
        sys.exit(1)

    # 6. 第二步：使用 PyInstaller 打包
    print("\n📦 正在使用 PyInstaller 打包...")

    # 找到 PyArmor 生成的运行时文件夹
    runtime_folder = None
    for item in os.listdir(pyarmor_dist):
        if item.startswith('pyarmor_runtime_'):
            runtime_folder = os.path.join(pyarmor_dist, item)
            break

    if not runtime_folder:
        print("❌ 错误：未找到 PyArmor 运行时文件夹")
        sys.exit(1)

    # 准备路径和参数
    encrypted_main = os.path.join(pyarmor_dist, 'main_encrypted.py')
    sep = ';' if sys.platform.startswith('win') else ':'
    icon_path = os.path.join(PROJECT_ROOT, 'src', 'pyauto', 'imgs', 'favicon.ico')
    icon_arg = [f'--icon={icon_path}'] if os.path.exists(icon_path) else []
    # 构建 PyInstaller 参数列表
    args = [
        os.path.join(ENCRYPTED_DIR, 'main_auto.py'), # 使用绝对路径指向入口文件
        *icon_arg,
        # '--clean',
        '--name=py-auto-encrypted',
        '--onefile',
        '--noconsole',
        '--noconfirm',
        '--distpath=dist',
        '--upx-exclude', 'adb.exe',
        '--upx-exclude', 'AdbWinApi.dll',
        '--upx-exclude', 'AdbWinUsbApi.dll',
        '--collect-all', 'uiautomator2',
        '--collect-all', 'psutil',
        '--exclude', 'resource',         # 排除 resource 文件夹
        '--exclude', 'test',         # 排除 test 文件夹
        '--collect-all', 'rapidocr',
        '--hidden-import', os.path.basename(runtime_folder),
    ]

    # 添加数据文件
    # 1. 将加密后的整个包打包进去，目标文件夹名为 pyauto
    args.append(f'--add-data={os.path.join(pyarmor_dist, "pyauto")}{sep}pyauto')

    # 2. 将 PyArmor 运行时文件夹打包到根目录
    runtime_folder_name = os.path.basename(runtime_folder)
    args.append(f'--add-data={runtime_folder}{sep}{runtime_folder_name}')

    # 3. 添加项目其他资源文件
    for src, dest in DATA_LIST:
        args.append(f'--add-data={src}{sep}{dest}')

    # 执行打包
    print(f"\n⚙️ 正在执行 PyInstaller 命令...")
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args)
        # PyInstaller 打包后的默认输出目录
        DIST_DIR = os.path.join(PROJECT_ROOT, "encrypted","dist")
        print(f"✅ 打包完成！EXE 文件位于: {DIST_DIR}")
        # --- 4. 复制 license.dat 到目标目录 ---
        print(f"📂 正在复制 {SOURCE_LICENSE} 到目标目录...")

        # 确保源文件存在
        if not os.path.exists(SOURCE_LICENSE):
            print(f"❌ 错误：找不到源文件 {SOURCE_LICENSE}")
            sys.exit(1)


        # 目标 config 文件夹路径 (在 exe 旁边)
        TARGET_CONFIG_DIR = os.path.join(DIST_DIR, "config")
        TARGET_LICENSE = os.path.join(TARGET_CONFIG_DIR, "license.dat")

        # 创建目标 config 文件夹 (如果不存在)
        os.makedirs(TARGET_CONFIG_DIR, exist_ok=True)

        # 执行复制
        shutil.copy2(SOURCE_LICENSE, TARGET_LICENSE)
        print(f"✅ 成功！文件已复制到: {TARGET_LICENSE}")

        print("\n🎉 构建成功！")
        print(f"👉 生成的单文件位于: dist/py-auto-encrypted.exe")
    except Exception as e:
        print(f"\n❌ 构建失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    build()