import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def get_resend_api_key() -> str:
    return getattr(settings, "IP_GUARD_RESEND_API_KEY", "")


def get_email_from_address() -> str:
    return getattr(settings, "IP_GUARD_EMAIL_FROM", "IP Guard <noreply@ipguard.dev>")


def get_frontend_base_url() -> str:
    return getattr(settings, "IP_GUARD_FRONTEND_BASE_URL", "http://localhost:5173")


def send_verification_email(user_email: str, token: str, username: str) -> bool:
    api_key = get_resend_api_key()
    if not api_key:
        logger.warning("Resend API key not configured, skipping email send")
        return False

    verify_url = f"{get_frontend_base_url()}/verify-email?token={token}"

    payload = {
        "from": get_email_from_address(),
        "to": [user_email],
        "subject": "邮箱验证 - IP Guard",
        "html": f"""
        <div style="max-width:600px;margin:0 auto;font-family:sans-serif;padding:20px;">
            <h2 style="color:#1a1a1a;">邮箱验证</h2>
            <p>您好 <strong>{username}</strong>，</p>
            <p>您正在修改 IP Guard 账号的邮箱地址，请点击下方按钮完成验证：</p>
            <div style="text-align:center;margin:30px 0;">
                <a href="{verify_url}"
                   style="background:#409eff;color:#fff;padding:12px 32px;border-radius:6px;text-decoration:none;font-size:16px;">
                    验证邮箱
                </a>
            </div>
            <p style="color:#666;font-size:14px;">
                如果按钮无法点击，请复制以下链接到浏览器打开：<br/>
                <a href="{verify_url}">{verify_url}</a>
            </p>
            <p style="color:#999;font-size:13px;">此链接 24 小时内有效。如非本人操作，请忽略此邮件。</p>
        </div>
        """,
    }

    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info("Verification email sent to %s", user_email)
            return True
        else:
            logger.error("Failed to send email: %s %s", resp.status_code, resp.text)
            return False
    except Exception:
        logger.exception("Error sending verification email")
        return False
