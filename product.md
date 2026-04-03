产品提交AI相关需求及记录

# ADB安装下载
Windows 系统
- 步骤 1：下载工具包
  官方下载地址（推荐）：https://developer.android.com/studio/releases/platform-tools
  （下滑找到「Download SDK Platform-Tools for Windows」，无需登录，直接下载 zip 包）
  备用地址（国内可访问）：https://developer.android.google.cn/studio/releases/platform-tools
- 步骤 2：解压并配置环境变量
  将下载的 platform-tools-latest-windows.zip 解压到固定路径（如 C:\platform-tools，建议路径无中文 / 空格）；
- 配置环境变量：
  右键「此电脑」→「属性」→「高级系统设置」→「环境变量」；
  在「系统变量」中找到 Path，点击「编辑」→「新建」；
- 验证：打开新的命令提示符（CMD），输入：
    ```
    adb version
    ``` 
  若显示版本信息（如 Android Debug Bridge version 1.0.41），说明配置成功。



# 生成requirement.txt

1. 安装 pipreqs
```bash
pip install pipreqs
```
2. 生成 requirements.txt
```bash
pipreqs .
```
. 代表当前目录。
执行后，它会自动扫描所有 Python 文件，并在当前目录生成一个 requirements.txt 文件。
3. (可选) 强制覆盖
   如果目录下已经有一个 requirements.txt 文件，你想重新生成并覆盖它，请加上 --force 参数：

```bash
pipreqs src/pyauto --force --ignore=.venv,env,__pycache__,*.pyc,*.log,*.json
```
这将告诉 pipreqs 跳过虚拟环境和缓存文件，只扫描你的源代码。

# 方案一：使用 pyproject.toml 进行“可编辑安装” (最推荐，现代标准)
关键一步：在终端运行以下命令（激活虚拟环境后）：
```bash
pip install -e .
```
-e 代表 "editable"（可编辑模式）。这意味着你对代码的任何修改都会立即生效，就像直接运行一样，但 Python 已经将其注册为系统包了。


# ADB相关命令
```bash
# 停止ADB服务
adb kill-server

# 启动ADB服务
adb start-server

# 再次查看设备
adb devices
```


# 功能需求
Python + uiautomator2 + weditor + MySQL + OCR
注意保留main.py和config_manager.py原有功能
## 1.打赏跳转页面
关联代码：main.py
菜单页增加打赏作者菜单，跳转指定url页面，直接在main.py

## 2.功能管理页面
### 2.1 定制任务
关联代码：function_manage_page.py,config_manager.py,main.py
不在main.py,在./page目录下创建功能管理页面，再被main.py应用
功能管理页面头部存在“保存所有”数据按钮
收集设备对应的json内容调用config_manager.py 的save_config

每个设备对应一个卡片内容
卡片上方是json 或者键值填写框
卡片下方是2个按钮：转换和保存
卡转换：片内容可以切换为json或者键值填写框
根据json配置固定的键不可填写，即转换为键值填写时键为不可填
其他：每个设备无对应数据时默认json配置
例如
{
"device_id_1": {"app_types": "xx1", "op_types": "功能1"},
"device_id_2": {"app_types": "xx1, xxx2"], "op_types": "功能1,功能2"}
}
其中device_id_1为设备id，{"app_types": "xx1", "op_types": "功能1"}为其json数据

### 2.2 任意json支持
关联代码：function_manage_page.py config_manager.py
优化支持json中可以任意修改包括增加key，不一定是app_types和op_types，键值转换时需要对应转换。

### 2.3 关联设备id 
关联代码：adb.py,function_manage_page.py,config_manager.py
卡片增加逻辑：
先按DeviceConfigManager()._configs配置卡片列表
然后再获取AdbManager.get_devices()的新设备id生成卡片，注意重复的设备id不生成卡片
如果不在AdbManager.get_devices()的设备id的卡片有删除按钮，可以删除掉DeviceConfigManager()._configs的配置
其他功能：头部增加刷新设备按钮

## 3.日志问题
关联代码：card_page.py
1.控制台日志输出到./log/py-auto.log
2.card_page.py中卡片的日志区只保留最新1000行日志
## 4.统一adb
关联代码：adb.py,card_page.py
把card_page.py的adb命令集成到adb.py中，优化adb.py统一使用项目内的./bin/adb.exe程序触发,保留功能不变

## 5.程序打包处理
worker_logic.py兼容打包为exe时脚本的读取情况
config_manager.py兼容打包为exe时脚本的读取情况
要实现 exe + bin + scripts 的结构
bin存放adb.exe
scripts存放py脚本
打包后 run_task 的执行情况和日志内容没在主线程控制台输出，打包前直接python运行是可以的
main.py 调用py a，a调用自定义工具类b，打包后的exe文件使用嵌入式包python的方式子进程调用scripts存放py的脚本e，那么e可以使用工具类b吗，已显式地告诉 Python 去 _internal 目录找模块
嵌入式包python的方式子进程调用第三方py脚本已显式地告诉 Python 去 _internal 目录找模块，该情况下main.py打包的exe使用的_internal的依赖会被e使用吗

asyncio + ProcessPoolExecutor + Queue
把subprocess 启动子进程调用py文件优化为进程池调用任务函数
要将架构优化为 asyncio + ProcessPoolExecutor + Queue，并实现进程池启动子任务、日志回传主线程UI，子进程内部检查停止信号，截图及其他功能不变
在 worker_logic.py 中，process_worker_entry 是专为多进程设计的入口函数。它负责：
创建独立的 asyncio 事件循环。
实例化 WorkerLogicAsync。
启动业务任务 (start_task) 和监控任务 (monitor_loop)。
处理日志队列的回传。
优化card_page实现正确调用纯多进程模型的WorkerLogicAsync，保持函数名类不变
注意能Queue 发送停止指令

## 6.模型加载问题
需要适配paddleocr，需要下载model，打包onefile方式支持，onedir方式支持

下载大小21mb

参考官方的文档
```html
https://www.paddleocr.ai/main/version3.x/pipeline_usage/OCR.html
```

```python
ocr_engine = PaddleOCR(lang='ch',
                                            text_detection_model_name="PP-OCRv5_mobile_det",
                                            text_recognition_model_name="PP-OCRv5_mobile_rec",
                                            # use_doc_orientation_classify=True,
                                            use_textline_orientation=True,
                                            textline_orientation_model_name='PP-LCNet_x1_0_textline_ori',
                                            )
```
下载165mb
```python
ocr_engine = PaddleOCR(lang='ch',
                       text_detection_model_name="PP-OCRv5_mobile_det",
                       text_recognition_model_name="PP-OCRv5_server_rec",
                       use_doc_orientation_classify=True,
# use_doc_orientation_classify=True,
                       use_textline_orientation=True,
                       textline_orientation_model_name='PP-LCNet_x1_0_textline_ori',
                       )

```
CPU：
配置	平均每图耗时（s）	平均每秒预测字符数量	平均 CPU 利用率（%）	峰值 RAM 用量（MB）	平均 RAM 用量（MB）
v5_mobile	1.75	371.82	965.89	2219.98	1830.97
v4_mobile	1.37	444.27	1007.33	2090.53	1797.76
v5_server	4.34	149.98	990.24	4020.85	3137.20
v4_server	5.42	115.20	999.03	4018.35	3105.29
说明：PP-OCRv5 的识别模型使用了更大的字典，需要更长的推理时间，导致 PP-OCRv5 的推理速度慢于 PP-OCRv4。


实际内存占用：即使是 mobile 模型，PaddleOCR 在 Python 进程中的实际内存占用通常在 300MB - 600MB 之间（取决于是否启用了 GPU、是否加载了方向分类器等）。
目前的代码结构在多进程（Multi-Processing）环境下运行
架构：根据 worker_logic.py，你为每个设备（模拟器）启动了一个独立的 Process（进程）。
内存机制：操作系统会给每个进程分配独立的内存空间。进程 A 和 进程 B 的内存是完全不互通的。
后果：
进程 1 (设备1)：加载 PaddleOCR 模型 -> 占用 xxx 内存。
进程 2 (设备2)：由于看不到进程 1 的内存，它必须重新加载模型 -> 又占用 xxx 内存。
进程 N (设备N)：以此类推。

## 7.atx-agent的apk安装问题 
uiautomator2 3.x 新项目自动安装需要的 atx 小车图标（ATX 应用）。
一、核心变化（3.x 架构重构）
彻底移除 atx-agent 常驻服务，调用相关功能时会自动安装 ATX 应用。
服务运行方式：改为运行时动态启动 uiautomator 服务（通过 adb 直接拉起 u2.jar），无界面、后台运行。
初始化逻辑：python -m uiautomator2 init 现在只推送必要的 jar 包与工具，不再安装任何可见应用。
二、为什么这样设计
简化部署：减少安装步骤，避免权限弹窗与厂商安全拦截。
降低资源占用：无常驻后台进程，更省电、更稳定。
提升兼容性：适配高版本 Android 权限机制。