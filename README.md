# 1.说明
多设备自动化控制与数据采集辅助工具

github开源地址：https://github.com/brightChenGit/py-auto-android

博客地址：https://www.brightchen.top/3494cdb3.html

联系方式：1024347104@qq.com

打赏地址：https://www.brightchen.top/pyauto/

## 项目简介
本项目是基于 Python 开发的**通用安卓设备自动化操作框架**，提供多设备管理、界面控制、屏幕识别、数据本地存储等基础能力，仅面向企业内部测试、设备运维与合法数据采集场景使用。

本项目**不内置任何业务脚本、不针对任何第三方App、不提供爬取逻辑**，所有业务逻辑均由使用者自行开发。

基础功能： 多设备投屏中心，支持投屏查看设备运行，支持自定义设备任务内容，每个设备单进程进行任务处理，支持MySQL数据保存，OCR识别，每个设备日志任务输出


## 技术栈
- Python 3.11.9
- uiautomator2
- uiautodev（调试工具）
- MySQL
- OCR 文字识别
- 多设备并行管理

## 核心功能
- 多台安卓设备批量连接与状态管理
- 模拟点击、滑动、输入等基础 UI 操作
- 控件获取、页面结构解析
- 屏幕截图与 OCR 文本识别
- 结构化数据存储至 MySQL
- 任务调度、日志记录、异常处理

## 使用范围（重要）
本工具**仅限内部局域网使用**：
- 仅用于合法持有设备的测试与运维
- 仅用于公开、非敏感信息的合法采集
- 仅用于内部研究、效率提升、自动化验证
- 不传播、不售卖、不用于公网服务

## 严格禁止行为
本工具为通用技术框架，严禁用于以下场景：
- 破解、逆向、Hook、抓包、绕过安全策略
- 批量高频访问、对服务端造成异常压力
- 采集用户隐私信息、个人信息、商业秘密
- 用于不正当竞争、数据倒卖、营销骚扰
- 违反平台用户协议与相关法律法规

## 责任声明
1. 本项目仅提供基础自动化能力，**不包含任何针对特定应用的采集逻辑**。
2. 使用者自行编写的业务脚本、采集规则、访问行为均由使用者独立负责。
3. 任何违规使用、越权访问、非法获取数据行为，均与本工具开发者无关。
4. 使用即代表已阅读并同意遵守相关法律条款与平台协议。


# 2.功能说明

菜单如下
- 投屏管理
    - 刷新设备列表 按钮
        - 刷新当前设备列表，加载更多的设备，再使用"重启ADB"按钮后可以使用，或者设备usb转wifi后刷新使用
    - 重启ADB 按钮
        - 启动ADB服务，连接设备，一般需要先启动
    - 一键启动所有 按钮
        - 启动所有设备的任务，任务设置由"任务管理"菜单按设备去配置
    - 一键停止所有 按钮
        - 停止所有设备的任务
    - 设备卡片列表功能
        - 头部:左侧为设备ID，中间为任务内容，右边为状态
        - 中部:投屏区域
        - 按钮区：
            - 关闭投屏/启动投屏 按钮：投屏是否开启
            - 转WIFI/WIFI 按钮：手机USB转WIFI链接
            - 启动任务 按钮：启动当前设备任务
            - 关闭任务 按钮：关闭当前设备任务
        - 底部：
            - 当前设备日志区
- 任务管理
    - 头部菜单
        - 刷新设备 按钮：刷新当前设备列表展示保存的设备数据
        - 保存所有设备配置 按钮：保存所有设备配置
    - 设备卡片列表
        - 头部：
            - 设备ID
            - 删除当前设备配置按钮
        - 中部：
            - 键值对配置任务内容
            - 键值对配置右侧为圆圈型的删除当前键值对按钮
            - 添加字段按钮
        - 底部
            - 转换JSON/转换键值 按钮：把中部的键值对转为json，或者从json转为键值对使用
            - 保存 按钮：保存当前设备按钮
- UI控件管理：待开发

# 3.安装配置说明

## 1.自定义的脚本代码编写
在`src/pyauto/scripts/`目录下编写任务，下面是参考模板
- src/pyauto/scripts/
    - config ---配置目录
        - base_config.py ---脚本配置，如脚本关联的数据库配置
    - dao ---数据层目录
        - mysql_dao.py ---执行sql
    - job ---任务目录
        - xxx.py ---具体任务
    - util ---工具类目录
    - vo ---ui视图目录
        - - xxxVo.py ---具体任务的视图层
    - task_runner.py ---固定入口函数，必须实现run_business_logic函数




## 2.安装
### 方法一
```bash  
# 1. 升级 pip (推荐，防止安装报错)  
python -m pip install --upgrade pip  
  
# 2. 安装依赖  
pip install -r requirements.txt  
```  

### 方法二
```bash  
# 安装核心自动化库  
pip install -U uiautomator2  
  
# 安装编辑器工具 (用于抓取元素)  
pip install -U weditor  
  
# 安装数据库驱动 (推荐 pymysql 或 mysql-connector-python)pip install pymysql sqlalchemy  
  
# 安装 OCR 库 (推荐 PaddleOCR，中文效果最好)  
pip install paddlepaddle paddleocr  
  
pip install PySide6  
  
pip install pyinstaller  
  
pip install qasync  
  
pip install DBUtils  
```  


## 3. dev 环境
创建虚拟环境
```bash
python -m venv .venv
```
  
激活虚拟环境  
```bash
 .\.venv\Scripts\activate  
```

退出虚拟环境

```bash  
deactivate  
```

## 4.项目运行

```bash  
python src/pyauto/main.py
```  
  
## 5.项目打包  
  
```bash  
 python build_file.py  
```  
打包后目录结构  
py-auto.exe ---运行文件  
config ---配置目录
- device_configs.json ---所有设备任务配置文件记录
    - 任务配置文件内容格式
```bash   
  {  
        "设备id1": {  
        "xxx": "xxx",        },        
        "设备id2": {  
        "xxx": "xxx",        },     
   }  
```
- logs ---日志目录
- py-auto.log ---所有设备运行日志文件



## 6.设备准备/模拟器准备
首次需要配置
- 1.开启 开发者选项。
- 2.开启 USB 调试（模拟器可以跳过该步骤）。
- 3.连接电脑，执行"重启ADB"按钮，确认连接，再点击"刷新设备列表"按钮，刷新出设备列表
- 4.先点击设备卡片的"启动任务"按钮，空跑任务，来自动安装atx的apk应用,允许安装
- 5.安装完毕之后进入手机设置允许输入法`adbkeyboard`(真实手机需要，模拟器可以直接使用)，这时候就可以使用了
- 6.其他流程，usb转wifi：
    - 流程首页菜单的设备卡片中点击""转wifi" 按钮，日志区提示可以断开后，可以断开usb链接，再点击"刷新设备列表"按钮即可

PS：
```bash  
ATX应用（通常指手机端安装的 atx-agent 及相关服务），其核心作用是充当 PC端 Python 脚本与 Android 设备之间的“桥梁”和“执行者”。  
自带快速输入法adbkeyboard  
```  



## 7.uiautodev代替weditor 调试开发
安装调试开发工具
```bash  
pip3 install -U uiautodev -i https://pypi.doubanio.com/simple
```  

启动方法一：
```bash  
uiauto.dev  
```  
启动方法二：
```bash  
python3 -m uiautodev
```  

## 8.其他说明
已封装paddleOrc工具类和其PP-OCRv5 mobile模型，已封装myssql的工具类，adb的工具类和日志的工具类

models
src/pauto/utils/ocr_util.py  
src/pauto/utils/mydb.py  
src/pauto/utils/adb.py  
src/pauto/utils/logUtil.py


