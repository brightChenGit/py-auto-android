# gen_rsa_keys.py
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def gen_rsa_keys():

    print("🔑 正在生成 RSA 密钥对...")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # 1. 保存私钥（⚠️ 绝对不要发给任何人，不要打包进 exe！）
    with open("private_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # 2. 保存公钥（这个可以公开，用于打包进 exe）
    with open("public_key.pem", "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    print("✅ 密钥对生成完毕！")
    print("🔒 私钥已保存为: private_key.pem (请妥善保管)")
    print("🔓 公钥已保存为: public_key.pem")

if __name__ == '__main__':
    gen_rsa_keys()