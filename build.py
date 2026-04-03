import os
import sys
import PyInstaller.__main__
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
def build():
    print("🚀 开始构建项目...")

    # 1. 获取项目根目录 (setup.py 所在的上一级目录)
    # 假设 setup.py 位于项目根目录下
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

    # 2. 定义需要打包的资源文件 (源路径, 目标路径)
    # PyInstaller 会将源路径的文件复制到输出目录的对应目标路径下
    DATA_LIST = [
        # ADB 工具目录
        (os.path.join(PROJECT_ROOT, 'src', 'pyauto', 'bin'), 'bin'),
        # OCR 模型目录 (核心资源)
        (os.path.join(PROJECT_ROOT, 'models'), 'models'),
    ]

    # 3. 检查资源目录是否存在 (防止漏打包或路径错误)
    print("🔍 正在检查资源目录...")
    for src, dest in DATA_LIST:
        if not os.path.exists(src):
            print(f"❌ 错误：资源目录未找到 -> {src}")
            print(f"💡 请确保目录结构正确，或者在 setup.py 中修正路径。")
            sys.exit(1) # 退出构建
        print(f"✅ 找到资源: {src} -> (打包后: {dest})")

    # 4. 定义 PyInstaller 参数
    # 注意：--onedir 是默认行为，但显式声明更清晰
    args = [
        'src/pyauto/main.py', # 入口文件
        '--icon=src/pyauto/img/favicon.ico'
        '--name=py-auto',    # 输出的程序名

        '--onedir',           # [关键] 使用单目录模式 (适合大文件)
        # '--onefile',        # 注释掉：不适合包含大模型的场景
        '--collect-all', 'uiautomator2', # 收集uiautomator2资源
        #自动收集 paddleocr 及其模型加载依赖 ---
        # 防止 PaddleOCR 运行时找不到动态库或配置
        '--collect-all', 'paddleocr',
        '--noconsole',            # 不显示控制台窗口 (如果是命令行工具请去掉此行)
        # '--windowed',         # 隐藏控制台 (如果不需要黑框)
        '--noconfirm', # 自动确认覆盖，不再询问

        '--distpath=dist',    # 输出目录
    ]

    # 5. 添加数据文件参数
    # PyInstaller 的 --add-data 格式为: 源路径;目标路径 (Windows用;，Mac/Linux用:)
    for src, dest in DATA_LIST:
        # 自动处理不同系统的分隔符
        sep = ';' if sys.platform.startswith('win') else ':'
        args.append(f'--add-data={src}{sep}{dest}')

    # 6. 执行打包
    print(f"\n⚙️  正在执行 PyInstaller 命令...")
    print(" ".join(args))

    try:
        PyInstaller.__main__.run(args)
        print("\n🎉 构建成功！")
        print(f"👉 可执行文件位于: {os.path.join('dist', '')}")
    except Exception as e:
        print(f"\n❌ 构建失败: {e}")

if __name__ == '__main__':
    build()