# license_manager.py
import json
import os
import hashlib
import subprocess
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import psutil

# 【重要】：将 public_key.pem 中的全部内容复制到这里（包含 BEGIN 和 END 行）
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2P+IyWHir8RjRmSAVk32
zUkiZ8iAoYcX6M3R29OYywoBPf8AUPkS7PWDG0q8haZBbDEGMAwnqtoxig/+Wj/Q
YaotQI7Gon3RaJMGcTroc1Ra8wwE47PW0Pg0/2IkcV2rn+pzgAZajSMtI0EZ3j8A
Un4T6+WtPep22Hr2WXv3JPwUU4Kqh6urEVMNgGDlrDMuLzJWz5vjC3C76N4CvBnB
Czh7UMcXkpeQnYX4xDY7z27/cbXqHMkToVcq0klIEDzwCah+skMwap2vzcRGtEGx
1pa6zQ+m1eu1RgXConsm6gTR7HOEM7kluv114NneMGd8dv3wLEWIl554Fhcag92f
lQIDAQAB
-----END PUBLIC KEY-----"""

class LicenseManager:
    def __init__(self, license_file="license.dat"):
        self.license_file = license_file

    def get_machine_code(self):
        """获取当前机器的唯一硬件指纹"""
        mac_addr = None
        mac = psutil.net_if_addrs()
        for interface, addrs in mac.items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK and addr.address and not interface.startswith(("lo", "veth", "docker")):
                    mac_addr = addr.address
                    break
            if mac_addr:
                break

        disk_serial = ""
        if os.name == 'nt':
            try:
                result = subprocess.run(['wmic', 'diskdrive', 'get', 'serialnumber'], capture_output=True, text=True)
                lines = [line.strip() for line in result.stdout.split('\n') if line.strip() and 'SerialNumber' not in line]
                if lines:
                    disk_serial = lines[0]
            except Exception:
                pass

        raw_data = f"{mac_addr}-{disk_serial}"
        return hashlib.sha256(raw_data.encode()).hexdigest()[:32]

    def verify_license(self):
        """校验授权文件"""
        if not os.path.exists(self.license_file):
            return False, "未找到授权文件 (license.dat)"

        try:
            with open(self.license_file, "rb") as f:
                content = f.read()

            parts = content.split(b"|||SIGNATURE|||")
            if len(parts) != 2:
                return False, "授权文件格式错误"

            json_bytes, signature = parts[0], parts[1]

            # 读取公钥
            public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)

            # 使用公钥验证签名（如果数据被篡改或伪造，这里会直接报错）
            public_key.verify(
                signature,
                json_bytes,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )

            license_data = json.loads(json_bytes)

            # 校验机器码
            if "machine_code" in license_data:
                if license_data["machine_code"] != self.get_machine_code():
                    return False, "授权文件与当前机器不匹配"

            # 校验过期时间
            expire_date = datetime.strptime(license_data["expire_date"], "%Y-%m-%d")
            if datetime.now() > expire_date:
                return False, f"授权已过期 (过期时间: {license_data['expire_date']})"

            return True, "授权有效"

        except Exception as e:
            return False, f"授权文件无效或被篡改"