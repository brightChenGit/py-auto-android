# 加密打包模块

生成 RSA 密钥对
```shell
python gen_rsa_keys.py
```
按需生成许可证
调用[gen_license.py](gen_license.py)


运行setExe.py实现加密打包输出exe
先运行[scan_imports.py](scan_imports.py)，获取[main_other.py](main_auto.py)文件,实现导入所有第三方库
然后再运行[build_file_encrypted.py](build_file_encrypted.py)

实现加密所有核心代码，然后打包为exe
