# mail_utils.py

import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

# 1. 导入配置管理器
from pyauto.config.config_base import UnifiedConfigManager

# 假设 logger 已在其他地方定义，例如：
# from pyauto.utils.logUtil import get_logger
# logger = get_logger()
import pyauto.utils.logUtil

# 获取全局 logger 实例
logger = pyauto.utils.logUtil.get_logger()

def send_email_notification( title,content):
    """
    发送邮件通知
    """
    # 2. 从配置管理器中读取配置
    config = UnifiedConfigManager.get_config().get("email")
    local_name=UnifiedConfigManager.get_config().get("local_name")

    smtp_server = config.get("smtp_host", "smtp.qq.com")
    smtp_port = int(config.get("smtp_port", 465)) # 确保端口是整数
    sender_email = config.get("sender_email")
    sender_password = config.get("auth_code")



    # --- 优化开始 ---
    # 2. 获取并解析多个收件人邮箱
    # 读取配置中的字符串，例如 "a@example.com, b@example.com"
    receivers_str = config.get("receiver_email", sender_email)
    # 使用列表推导式分割并去除每个邮箱地址前后的空格
    receiver_emails = [email.strip() for email in receivers_str.split(',') if email.strip()]

    # 如果没有解析出任何有效邮箱，则默认发给发件人
    if not receiver_emails:
        receiver_emails = [sender_email]
    # --- 优化结束 ---

    # receiver_email = config.get("receiver_email", sender_email) # 如果未指定收件人，则默认发给发件人

    # 3. 检查必要配置是否存在
    if not all([sender_email, sender_password]):
        logger.error("[邮件通知] 配置错误：发件邮箱或授权码未设置，无法发送邮件。")
        return

    # --- 以下代码保持不变 ---

    # 1. 构造邮件内容
    subject = f"{title}"
    body = f"""尊敬的 {local_name}：\n
您好！\n
{content}\n
此致
敬礼\n
py-auto 团队
"""
    message = MIMEText(body, 'plain', 'utf-8')
    message['From'] = sender_email
    # message['To'] = Header(f"管理员<{receiver_email}>", 'utf-8')
    message['To'] = ", ".join(receiver_emails)
    message['Subject'] = Header(subject, 'utf-8')

    # 2. 尝试发送邮件
    server = None # 将 server 的初始化移到 try 外部
    try:
        # 智能连接逻辑
        if smtp_port == 25:
            # 针对 25 端口的企业内网网关
            logger.info(f"[邮件通知] 正在连接企业网关 {smtp_server}:{smtp_port}...")
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.ehlo()
        elif smtp_port == 587:
            logger.info(f"[邮件通知] 正在通过 STARTTLS 连接 {smtp_server}:{smtp_port}...")
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            # 对于 465 端口，会进入这个分支
            logger.info(f"[邮件通知] 正在通过 SSL 连接 {smtp_server}:{smtp_port}...")
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)

        # 只有在配置了密码的情况下才尝试登录
        if sender_password:
            try:
                server.login(sender_email, sender_password)
            except smtplib.SMTPNotSupportedError:
                logger.warning("[邮件通知] 服务器不支持 AUTH 登录，尝试匿名发送...")
        else:
            logger.info("[邮件通知] 未配置密码，使用匿名方式发送")

        # 发送邮件
        server.sendmail(sender_email, receiver_emails, message.as_string())
        logger.info(f"[邮件通知] 邮件已成功发送至 {receiver_emails}")

    except smtplib.SMTPAuthenticationError:
        logger.error("[邮件通知] 认证失败：请检查邮箱账号或授权码是否正确。")
    except Exception as e:
        logger.error(f"[邮件通知] 发送邮件失败: {e}")
    finally:
        # 【关键修改】无论成功或失败，都确保关闭连接
        if server:
            try:
                server.quit()
                # logger.info("[邮件通知] SMTP 连接已关闭。")
            except Exception as e:
                logger.warning(f"[邮件通知] 关闭 SMTP 连接时发生异常: {e}")


if __name__ == '__main__':
    send_email_notification("【系统通知】这是一封来自 py-auto 的测试邮件",f"尊敬的用户：您好！这是一封用于测试邮件发送功能的邮件，请忽略。当前时间：{datetime.now()}")