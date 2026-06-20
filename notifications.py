"""邮件通知。

通过 config.py / 环境变量配置 SMTP。未配置 SMTP_HOST 时自动降级：
只在控制台打印日志，不发送、也不会让请求报错。
短信通知需要第三方服务商（阿里云短信、Twilio 等），可在 send_sms 中接入。
"""

import smtplib
from email.message import EmailMessage

from flask import current_app, url_for


def email_enabled():
    return bool(current_app.config.get("SMTP_HOST"))


def send_email(to_address, subject, body):
    """发送纯文本邮件，返回是否真正发送成功。"""
    if not to_address:
        return False
    if not email_enabled():
        current_app.logger.info("SMTP 未配置，跳过邮件发送：to=%s subject=%s", to_address, subject)
        return False

    config = current_app.config
    message = EmailMessage()
    message["From"] = config["MAIL_FROM"]
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"], timeout=10) as server:
            if config["SMTP_USE_TLS"]:
                server.starttls()
            if config["SMTP_USER"]:
                server.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
            server.send_message(message)
        return True
    except Exception as exc:  # noqa: BLE001 - 通知失败不应影响主流程
        current_app.logger.warning("邮件发送失败：%s", exc)
        return False


def send_sms(phone, body):
    """短信通知占位接口：需接入第三方服务商后实现。"""
    current_app.logger.info("短信通道未接入，跳过短信发送：to=%s", phone)
    return False


def notify_new_message(message_row, post, sender, receiver):
    """有人发来新私信时通知接收方。"""
    if not receiver or not receiver.email or not receiver.notify_email:
        return False
    try:
        link = current_app.config["SITE_BASE_URL"].rstrip("/") + url_for(
            "chat", post_id=post.id, other_id=sender.id
        )
    except Exception:  # noqa: BLE001 - 拼接链接失败时退回站点首页
        link = current_app.config["SITE_BASE_URL"]

    subject = f"[校园失物招领] {sender.name} 给你发来一条私信"
    body = (
        f"{receiver.name} 你好：\n\n"
        f"{sender.name}（{sender.student_no}）就帖子《{post.title}》给你发来一条私信：\n\n"
        f"    {message_row.content}\n\n"
        f"点击查看并回复：{link}\n\n"
        "如不想再收到此类邮件，可在系统中关闭邮件通知。"
    )
    return send_email(receiver.email, subject, body)


def notify_password_reset(student, token):
    """发送找回密码邮件，返回是否发送成功。"""
    if not student.email:
        return False
    link = current_app.config["SITE_BASE_URL"].rstrip("/") + url_for(
        "reset_password", token=token
    )
    subject = "[校园失物招领] 重置密码"
    body = (
        f"{student.name} 你好：\n\n"
        f"我们收到了你的重置密码请求。请点击以下链接在 30 分钟内重置密码：\n\n"
        f"    {link}\n\n"
        "如果不是你本人操作，请忽略此邮件。"
    )
    return send_email(student.email, subject, body)
