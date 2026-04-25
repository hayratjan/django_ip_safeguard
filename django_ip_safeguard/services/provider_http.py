import time
from typing import Optional

import httpx

from django_ip_safeguard.exceptions import ProviderError
from django_ip_safeguard.services.provider_base import BaseIpIntelProvider
from django_ip_safeguard.types import IpIntel


class DummyIpIntelProvider(BaseIpIntelProvider):
    """
    默认 Provider。
    说明：当前仅作为工程骨架，后续替换为真实 HTTP API 对接实现。
    """

    def fetch_ip_intel(self, ip: str) -> IpIntel:
        return IpIntel(ip=ip, country_code="UNKNOWN", risk_score=0, risk_tags=[], source="dummy")


class HttpIpIntelProvider(BaseIpIntelProvider):
    """
    通用 HTTP Provider（支持连接池复用）。
    约定返回 JSON 字段：
    - country_code: 国家码（如 CN）
    - risk_score: 风险分（整数）
    - risk_tags: 风险标签列表
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str = "",
        timeout: float = 3.0,
        max_retries: int = 2,
        retry_backoff: float = 0.2,
        headers: Optional[dict] = None,
        pool_limits: Optional[dict] = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff = max(0.0, float(retry_backoff))
        self.headers = headers or {}
        # 复用连接池，减少 TCP 握手开销
        limits = httpx.Limits(
            max_connections=pool_limits.get("max_connections", 20) if pool_limits else 20,
            max_keepalive_connections=pool_limits.get("max_keepalive", 10) if pool_limits else 10,
        )
        try:
            self._client = httpx.Client(timeout=self.timeout, limits=limits)
        except TypeError:
            # 兼容旧版 httpx（不支持 limits 参数）及仅接受 timeout 的测试桩
            self._client = httpx.Client(timeout=self.timeout)

    def fetch_ip_intel(self, ip: str) -> IpIntel:
        if not self.endpoint:
            raise ProviderError("HTTP Provider 未配置 IP_GUARD_PROVIDER_ENDPOINT")

        request_headers = dict(self.headers)
        if self.api_key and "Authorization" not in request_headers:
            request_headers["Authorization"] = f"Bearer {self.api_key}"

        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.get(
                    self.endpoint,
                    params={"ip": ip},
                    headers=request_headers,
                )
                response.raise_for_status()
                payload = response.json()
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= self.max_retries:
                    error_type = type(exc).__name__
                    raise ProviderError(f"HTTP Provider 请求失败[{error_type}]: {exc}") from exc
                sleep_seconds = self.retry_backoff * (2**attempt)
                time.sleep(sleep_seconds)
        else:
            error_type = type(last_exc).__name__ if last_exc else "Unknown"
            raise ProviderError(f"HTTP Provider 请求失败[{error_type}]: {last_exc}")

        return IpIntel(
            ip=ip,
            country_code=str(payload.get("country_code", "UNKNOWN")).upper(),
            risk_score=int(payload.get("risk_score", 0)),
            risk_tags=list(payload.get("risk_tags", [])),
            source="http",
        )

    def close(self) -> None:
        """关闭连接池，释放资源。"""
        self._client.close()
