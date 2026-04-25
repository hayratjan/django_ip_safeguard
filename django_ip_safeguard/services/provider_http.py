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
    通用 HTTP Provider。
    约定返回 JSON 字段：
    - country_code: 国家码（如 CN）
    - risk_score: 风险分（整数）
    - risk_tags: 风险标签列表

    每次 fetch 内创建并关闭 httpx.Client，避免长驻连接池在进程内永不释放。
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
        self._pool_limits = pool_limits

    def _open_http_client(self) -> httpx.Client:
        """创建短生命周期 Client；调用方须在 finally 中 close。"""
        pl = self._pool_limits
        limits = httpx.Limits(
            max_connections=pl.get("max_connections", 20) if pl else 20,
            max_keepalive_connections=pl.get("max_keepalive", 10) if pl else 10,
        )
        try:
            return httpx.Client(timeout=self.timeout, limits=limits)
        except TypeError:
            # 兼容旧版 httpx（不支持 limits 参数）及仅接受 timeout 的测试桩
            return httpx.Client(timeout=self.timeout)

    def fetch_ip_intel(self, ip: str) -> IpIntel:
        if not self.endpoint:
            raise ProviderError("HTTP Provider 未配置 IP_GUARD_PROVIDER_ENDPOINT")

        request_headers = dict(self.headers)
        if self.api_key and "Authorization" not in request_headers:
            request_headers["Authorization"] = f"Bearer {self.api_key}"

        client = self._open_http_client()
        try:
            last_exc = None
            for attempt in range(self.max_retries + 1):
                try:
                    response = client.get(
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
                        raise ProviderError(
                            f"HTTP Provider 请求失败[{error_type}]: {exc}"
                        ) from exc
                    sleep_seconds = self.retry_backoff * (2**attempt)
                    time.sleep(sleep_seconds)
            else:
                error_type = type(last_exc).__name__ if last_exc else "Unknown"
                raise ProviderError(f"HTTP Provider 请求失败[{error_type}]: {last_exc}")
        finally:
            client.close()

        return IpIntel(
            ip=ip,
            country_code=str(payload.get("country_code", "UNKNOWN")).upper(),
            risk_score=int(payload.get("risk_score", 0)),
            risk_tags=list(payload.get("risk_tags", [])),
            source="http",
        )
