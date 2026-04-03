import os
import sys
import PyInstaller.__main__

# 设置环境变量 (保持不变)
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

def build():
    print("🚀 开始构建项目...")

    # 1. 获取项目根目录
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

    # 2. 定义需要打包的资源文件 (源路径, 目标路径)
    # 注意：在 OneFile 模式下，目标路径决定了运行时在临时目录中的位置
    DATA_LIST = [
        # ADB 工具目录：建议直接映射到根目录，方便 main.py 查找
        (os.path.join(PROJECT_ROOT, 'src', 'pyauto', 'bin'), 'bin'),
        # OCR 模型目录 (核心资源)
        (os.path.join(PROJECT_ROOT, 'models'), 'models'),
    ]

    # 3. 检查资源目录是否存在
    print("🔍 正在检查资源目录...")
    for src, dest in DATA_LIST:
        if not os.path.exists(src):
            print(f"❌ 错误：资源目录未找到 -> {src}")
            print(f"💡 请确保目录结构正确，或者在 setup.py 中修正路径。")
            sys.exit(1) # 退出构建
    print("✅ 所有资源检查通过")

    # 4. 定义 PyInstaller 参数
    # 关键点：使用 --onefile，并排除 adb.exe 的 UPX 压缩
    args = [
        'src/pyauto/main.py', # 入口文件
        '--icon=src/pyauto/img/favicon.ico'
        '--name=py-auto',     # 输出的程序名
        '--onefile',          # [关键] 切换为单文件模式
        '--noconsole',      # 可选：如果不需要控制台
        # --- 自动收集 uiautomator2 及其 assets 资源 ---
        # 这会自动包含 u2.jar, atx-agent 等所有依赖，解决 "Resource assets/u2.jar not found" 错误
        '--collect-all', 'uiautomator2',
        # --- 自动收集 paddleocr 及其模型加载依赖 ---
        # 防止 PaddleOCR 运行时找不到动态库或配置
        '--collect-all', 'paddleocr',
        '--noconfirm',        # 自动确认覆盖
        '--distpath=dist',    # 输出目录
    ]

    # --- 特别处理：防止 adb.exe 被 UPX 压缩损坏 ---
    # 在 OneFile 模式下，PyInstaller 默认会使用 UPX 压缩所有 exe。
    # 但 adb.exe 被压缩后经常无法运行，因此必须排除
    if sys.platform.startswith('win'):
        args.extend(['--upx-exclude', 'adb.exe']) # 排除所有名为 adb.exe 的文件
        args.extend(['--upx-exclude', 'AdbWinApi.dll'])
        args.extend(['--upx-exclude', 'AdbWinUsbApi.dll'])
    # 5. 添加数据文件参数
    # PyInstaller 会将源路径的文件复制到输出目录的对应目标路径下
    for src, dest in DATA_LIST:
        # 自动处理不同系统的分隔符 (Windows用;，Mac/Linux用:)
        sep = ';' if sys.platform.startswith('win') else ':'
        # 格式: --add-data "源路径;目标路径"
        args.append(f'--add-data={src}{sep}{dest}')


    # 6. 执行打包
    print(f"\n⚙️ 正在执行 PyInstaller 命令...")
    print(" ".join(args))

    try:
        PyInstaller.__main__.run(args)
        print("\n🎉 构建成功！")
        print(f"👉 生成的单文件位于: dist/py-auto.exe")
    except Exception as e:
        print(f"\n❌ 构建失败: {e}")

if __name__ == '__main__':
    build()