import logging
import time

from django_ip_safeguard.services.cache import RedisCacheService

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """熔断器实现（关闭 → 打开 → 半开）。"""

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(
        self,
        cache_service: RedisCacheService,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
    ):
        self.cache = cache_service
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

    @staticmethod
    def _state_key() -> str:
        return "ip_guard:circuit:state"

    @staticmethod
    def _failures_key() -> str:
        return "ip_guard:circuit:failures"

    @staticmethod
    def _opened_at_key() -> str:
        return "ip_guard:circuit:opened_at"

    @staticmethod
    def _half_open_calls_key() -> str:
        return "ip_guard:circuit:half_open_calls"

    def current_state(self) -> str:
        try:
            state = self.cache.client.get(self._state_key())
            if state == self.STATE_OPEN:
                opened_at = self.cache.client.get(self._opened_at_key())
                if opened_at:
                    elapsed = time.time() - float(opened_at)
                    if elapsed >= self.recovery_timeout:
                        self.cache.client.set(self._state_key(), self.STATE_HALF_OPEN)
                        self.cache.client.set(self._half_open_calls_key(), "0")
                        return self.STATE_HALF_OPEN
                return self.STATE_OPEN
            return state or self.STATE_CLOSED
        except Exception:  # noqa: BLE001
            return self.STATE_CLOSED

    def record_success(self) -> None:
        try:
            state = self.current_state()
            if state == self.STATE_HALF_OPEN:
                self.cache.client.set(self._state_key(), self.STATE_CLOSED)
                self.cache.client.delete(self._failures_key())
                self.cache.client.delete(self._half_open_calls_key())
                logger.info("熔断器恢复：半开状态探测成功，切换到关闭状态")
            elif state == self.STATE_CLOSED:
                self.cache.client.delete(self._failures_key())
        except Exception:  # noqa: BLE001
            pass

    def record_failure(self) -> None:
        try:
            state = self.current_state()
            if state == self.STATE_HALF_OPEN:
                self.cache.client.set(self._state_key(), self.STATE_OPEN)
                self.cache.client.set(self._opened_at_key(), str(time.time()))
                logger.warning("熔断器打开：半开状态探测失败")
            elif state == self.STATE_CLOSED:
                failures = self.cache.client.incr(self._failures_key())
                if failures == 1:
                    self.cache.client.expire(self._failures_key(), self.recovery_timeout)
                if failures >= self.failure_threshold:
                    self.cache.client.set(self._state_key(), self.STATE_OPEN)
                    self.cache.client.set(self._opened_at_key(), str(time.time()))
                    logger.warning("熔断器打开：连续失败 %s 次", failures)
        except Exception:  # noqa: BLE001
            pass

    def allow_request(self) -> bool:
        state = self.current_state()
        if state == self.STATE_CLOSED:
            return True
        if state == self.STATE_OPEN:
            return False
        # 半开状态：只允许有限次数的探测请求
        try:
            calls = self.cache.client.incr(self._half_open_calls_key())
            if calls == 1:
                self.cache.client.expire(self._half_open_calls_key(), self.recovery_timeout)
            return calls <= self.half_open_max_calls
        except Exception:  # noqa: BLE001
            return False
