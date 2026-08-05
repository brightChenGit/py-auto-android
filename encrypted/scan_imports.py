import os
import re

# ==========================================
# 1. 配置区：根据你的项目实际情况修改
# ==========================================

# 你的核心源码目录（扫描的目标）
SOURCE_DIR = '../src/pyauto'

# 依赖黑名单：包含所有你确定不需要、或者会导致打包报错的包名
IGNORE_PACKAGES = {
    'aistudio-sdk',
    '.',
    'annotated-doc',
    'pywin32',
    # 如果你用的是 pywin32-ctypes，把 pywin32 加到黑名单
}

# 包名 -> 导入名 映射字典：处理包名和 import 名字不一致的情况
PACKAGE_TO_IMPORT = {
    'python_dateutil': 'dateutil',
    'beautifulsoup4': 'bs4',
    'Pillow': 'PIL',
    'scikit_learn': 'sklearn',
    'scikit_image': 'skimage',
    'PyYAML': 'yaml',
    'pywin32_ctypes': 'win32ctypes',
    'pycryptodome': 'Crypto',
    'protobuf': 'google.protobuf',
    'PySide6': 'PySide6',
    'pyside6': 'PySide6',
    'pyside6_essentials': 'PySide6',
    'pyside6_addons': 'PySide6',
    'opencv_contrib_python': 'cv2',
    'opencv_python': 'cv2',
    'huggingface_hub': 'huggingface_hub',
    'prompt_toolkit': 'prompt_toolkit',
    'py_cpuinfo': 'cpuinfo',
    'pydantic_core': 'pydantic_core',
    'python_bidi': 'bidi',
    'python_multipart': 'multipart',
    'typing_extensions': 'typing_extensions',
    'ruamel.yaml': 'ruamel.yaml',
    'antlr4_python3_runtime': 'antlr4',
    'charset_normalizer': 'charset_normalizer',
    'jupyter_client': 'jupyter_client',
    'jupyter_core': 'jupyter_core',
    'markdown_it_py': 'markdown_it',
    'stack_data': 'stack_data',
    'Flask': 'flask',
    'Requests': 'requests',
}

# 你的项目主包名，用于排除项目内部的相对导入
PROJECT_PACKAGE_NAME = 'pyauto'

# ==========================================
# 2. 核心逻辑区
# ==========================================

def scan_imports_from_source(source_dir):
    """
    扫描指定目录下所有 .py 文件，提取 import 语句
    现在会同时提取顶层包和深层子模块
    """
    print(f"🔍 正在扫描源码目录: {source_dir}")
    imports = set()

    # 匹配 import xxx
    import_pattern = re.compile(r'^\s*import\s+([\w\.]+)')
    # 匹配 from xxx import yyy
    from_pattern = re.compile(r'^\s*from\s+([\w\.]+)\s+import')

    for root, dirs, files in os.walk(source_dir):
        # 跳过常见的非源码目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'env', 'dist', 'build']]

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            # 检查 import xxx
                            match_import = import_pattern.match(line)
                            if match_import:
                                # 获取顶层模块名，例如从 PySide6.QtWidgets 中提取 PySide6
                                top_module = match_import.group(1).split('.')[0]
                                imports.add(top_module)
                                continue # 匹配到一种就不再检查另一种

                            # 检查 from xxx import yyy
                            match_from = from_pattern.match(line)
                            if match_from:
                                full_module = match_from.group(1)
                                # 关键逻辑：如果 from 后面跟的是多层模块，如 dbutils.pooled_db
                                # 我们就把它完整地加进去，而不仅仅是 dbutils
                                if full_module.count('.') > 0:
                                    imports.add(full_module)
                                else:
                                    # 否则，还是只加顶层模块
                                    imports.add(full_module)

                except Exception as e:
                    print(f"⚠️ 读取文件失败 {filepath}: {e}")

    return list(imports)

def filter_and_translate(libs):
    """
    过滤黑名单、项目内模块，并将包名翻译为正确的导入名，同时去重
    """
    print("🛠️ 正在过滤无用包并翻译导入名...")
    unique_imports = set()

    for package_name in libs:
        # 1. 检查是否在黑名单中
        if package_name in IGNORE_PACKAGES:
            print(f" 🚫 已忽略黑名单包: {package_name}")
            continue

        # 2. 检查是否是项目内部模块
        # 注意：这里要处理深层模块，比如 pyauto.utils，也要排除
        if package_name == PROJECT_PACKAGE_NAME or package_name.startswith(PROJECT_PACKAGE_NAME + '.'):
            print(f" 🚫 已忽略项目内模块: {package_name}")
            continue

        # 3. 从字典中获取正确的导入名，如果没有则默认使用包名
        # 对于深层模块，如 dbutils.pooled_db，我们只取顶层 dbutils 去映射
        top_level_package = package_name.split('.')[0]
        import_name = PACKAGE_TO_IMPORT.get(top_level_package, top_level_package)

        # 4. 如果是深层模块，需要把映射后的顶层包名和原来的子模块名拼回去
        if package_name.count('.') > 0:
            sub_modules = package_name.split('.')[1:]
            final_import_name = import_name + '.' + '.'.join(sub_modules)
        else:
            final_import_name = import_name

        # 5. 加入集合（自动去重）
        unique_imports.add(final_import_name)

    return sorted(list(unique_imports))

def generate_main_auto(clean_imports):
    """
    生成干净的 main_auto.py 文件
    """
    print("📝 正在生成 main_auto.py...")

    # 将列表转换为格式化的字符串，例如: "'PySide6', 'os', 'sys'"
    imports_str = ", ".join([f"'{mod}'" for mod in clean_imports])

    with open('main_auto.py', 'w', encoding='utf-8') as f:
        f.write('# main_auto.py\n')
        f.write('# 这是一个由 scan_imports.py 自动生成的干净入口文件\n')
        f.write('# 用于 PyInstaller 打包，以解决 PyArmor 加密后的依赖丢失问题\n\n')

        f.write('# --- 1. 导入所有第三方库 ---\n')
        f.write('# 这些 import 语句帮助 PyInstaller 扫描并打包所有依赖项\n')
        for imp in clean_imports:
            f.write(f'import {imp}\n')

        f.write('\n# --- 2. 动态加载被 PyArmor 加密的核心业务模块 ---\n')
        f.write('import sys\n')
        f.write('import os\n')
        f.write('import tkinter as tk\n')
        f.write('from tkinter import messagebox\n')
        f.write('import importlib.util\n\n')

        # 使用 f-string 将 imports_str 注入到生成的代码中
        f.write('''
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
        ''')

    print("✅ main_auto.py 生成完成！")
    print("💡 提示：请检查生成的文件，确认本地模块的导入是否需要手动补充。")

# ==========================================
# 3. 主程序入口
# ==========================================

if __name__ == '__main__':
    libs = scan_imports_from_source(SOURCE_DIR)
    if libs:
        clean_imports = filter_and_translate(libs)
        print(f"✅ 最终提取到 {len(clean_imports)} 个干净的第三方导入。")
        generate_main_auto(clean_imports)
    else:
        print("❌ 未能获取第三方库列表，生成终止。")