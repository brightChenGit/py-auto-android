# gen_license.py
import json
import argparse
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import shutil

def generate_license(expire_date, machine_code=None):
    license_data = {"expire_date": expire_date}
    if machine_code:
        license_data["machine_code"] = machine_code

    json_bytes = json.dumps(license_data).encode()

    # 读取私钥
    try:
        with open("private_key.pem", "rb") as key_file:
            private_key = serialization.load_pem_private_key(key_file.read(), password=None)
    except FileNotFoundError:
        print("❌ 错误：当前目录下未找到 private_key.pem 文件！")
        return

    # 使用私钥对数据进行签名
    signature = private_key.sign(
        json_bytes,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )

    # 将数据和签名打包写入文件
    with open("license.dat", "wb") as f:
        f.write(json_bytes + b"|||SIGNATURE|||" + signature)

    print(f"✅ 授权文件已生成: license.dat")
    print(f"⏳ 过期时间: {expire_date}")
    if machine_code:
        print(f"🔑 绑定机器码: {machine_code}")
    else:
        print(f"🌐 授权模式: 通用授权 (不限机器)")

    # 2. 开始复制文件
    target_dir = "../src/pyauto/config"
    try:
        shutil.copy("license.dat", target_dir)
        print(f"✅ 授权文件已成功复制到: {target_dir}")
    except Exception as e:
        print(f"❌ 复制文件失败: {e}")

if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description="生成软件授权文件")
    # parser.add_argument('--expire', type=str, required=True, help='过期时间 (YYYY-MM-DD)')
    # parser.add_argument('--machine', type=str, default=None, help='目标机器码 (留空则生成通用授权)')
    # args = parser.parse_args()

    # generate_license(args.expire, args.machine)
    generate_license("2099-12-31 00:00:00")
    # generate_license("2025-12-31 00:00:00")