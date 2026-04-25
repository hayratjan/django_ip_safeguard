from django_ip_safeguard.services.circuit_breaker import CircuitBreaker


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    def setex(self, key, ttl, value):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)

    def incr(self, key):
        current = int(self.data.get(key, 0))
        current += 1
        self.data[key] = str(current)
        return current

    def expire(self, key, ttl):
        return True


class FakeCacheService:
    def __init__(self):
        self.client = FakeRedis()


class TestCircuitBreaker:
    def test_closed_state_allows_requests(self, monkeypatch):
        cache = FakeCacheService()
        cb = CircuitBreaker(cache, failure_threshold=3, recovery_timeout=60)
        assert cb.allow_request() is True
        assert cb.current_state() == "closed"

    def test_opens_after_failures(self, monkeypatch):
        cache = FakeCacheService()
        cb = CircuitBreaker(cache, failure_threshold=3, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.allow_request() is True
        cb.record_failure()
        assert cb.current_state() == "open"
        assert cb.allow_request() is False

    def test_half_open_after_timeout(self, monkeypatch):
        cache = FakeCacheService()
        cb = CircuitBreaker(cache, failure_threshold=2, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.current_state() == "open"
        # 模拟时间流逝
        import time

        time.sleep(1.1)
        assert cb.current_state() == "half_open"
        assert cb.allow_request() is True

    def test_recovery_on_success(self, monkeypatch):
        cache = FakeCacheService()
        cb = CircuitBreaker(cache, failure_threshold=2, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        import time

        time.sleep(1.1)
        assert cb.current_state() == "half_open"
        cb.record_success()
        assert cb.current_state() == "closed"
        assert cb.allow_request() is True

    def test_half_open_failure_reopens(self, monkeypatch):
        cache = FakeCacheService()
        cb = CircuitBreaker(cache, failure_threshold=2, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        import time

        time.sleep(1.1)
        assert cb.current_state() == "half_open"
        cb.record_failure()
        assert cb.current_state() == "open"
