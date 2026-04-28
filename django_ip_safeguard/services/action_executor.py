"""把策略 / 风险引擎的 ``action`` 翻译成 ``HttpResponse``。

中间件原本散落多处构造 ``JsonResponse``，现在集中在这里：
- ``allow`` / ``log_only`` → 调用方应直接放行（本模块 ``build_response`` 会返回 ``None``）。
- ``block`` / ``ban`` → ``block_status_code`` 状态码。
- ``challenge`` → ``challenge_status_code`` 状态码（如 429）。
- ``rate_limit`` → 429。

同时按 ``Accept`` 头自动返回 JSON 或简单 HTML，避免浏览器拿到 JSON 看不懂。
"""

from __future__ import annotations

from typing import Optional

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.translation import gettext as _t

from django_ip_safeguard.conf import IpGuardSettings


def _wants_html(request: HttpRequest) -> bool:
    accept = (request.META.get("HTTP_ACCEPT") or "").lower()
    if "application/json" in accept:
        return False
    return "text/html" in accept


def _status_code_for(action: str, config: IpGuardSettings) -> int:
    if action == "rate_limit":
        return 429
    if action == "challenge":
        return int(config.challenge_status_code or 403)
    return int(config.block_status_code or 403)


def _html_body(reason: str, ip: str, status: int) -> str:
    return (
        "<!DOCTYPE html>"
        "<html><head><meta charset='utf-8'><title>Access blocked</title></head>"
        f"<body style='font-family:system-ui;padding:48px;'>"
        f"<h2 style='margin-bottom:8px;'>{_t('访问被安全策略阻止')}</h2>"
        f"<p style='color:#666;'>{_t('原因')}: {reason}</p>"
        f"<p style='color:#999;font-size:12px;'>IP: {ip}</p>"
        f"<p style='color:#999;font-size:12px;'>HTTP {status}</p>"
        "</body></html>"
    )


def build_response(
    request: HttpRequest,
    action: str,
    reason: str,
    ip: str,
    config: IpGuardSettings,
) -> Optional[HttpResponse]:
    """根据 action 构造响应；放行类返回 None，由调用方继续 ``get_response``。"""
    if action in {"allow", "log_only"}:
        return None

    status = _status_code_for(action, config)
    if _wants_html(request):
        return HttpResponse(_html_body(reason, ip, status), status=status, content_type="text/html; charset=utf-8")

    return JsonResponse(
        {
            "detail": str(_t("访问被安全策略阻止")),
            "reason": str(reason),
            "ip": ip,
            "action": action,
        },
        status=status,
    )


def is_block_action(action: str) -> bool:
    return action not in {"allow", "log_only"}
