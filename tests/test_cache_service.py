from django_ip_safeguard.services.cache import RedisCacheService


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)

    def ping(self):
        return True

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    def incr(self, key):
        current = int(self.data.get(key, 0))
        current += 1
        self.data[key] = str(current)
        return current

    def expire(self, key, ttl):
        return True


def test_lock_and_release(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("django_ip_safeguard.services.cache.redis.Redis.from_url", lambda *args, **kwargs: fake)
    cache = RedisCacheService("redis://fake")
    assert cache.acquire_intel_lock("1.1.1.1", 3) is True
    assert cache.acquire_intel_lock("1.1.1.1", 3) is False
    cache.release_intel_lock("1.1.1.1")
    assert cache.acquire_intel_lock("1.1.1.1", 3) is True


def test_provider_failure_counter(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("django_ip_safeguard.services.cache.redis.Redis.from_url", lambda *args, **kwargs: fake)
    cache = RedisCacheService("redis://fake")
    assert cache.get_provider_failures() == 0
    assert cache.increase_provider_failures(60) == 1
    assert cache.increase_provider_failures(60) == 2
    assert cache.get_provider_failures() == 2
    cache.clear_provider_failures()
    assert cache.get_provider_failures() == 0


def test_rate_limit_window(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("django_ip_safeguard.services.cache.redis.Redis.from_url", lambda *args, **kwargs: fake)
    cache = RedisCacheService("redis://fake")
    assert cache.is_rate_limited("1.1.1.1", 0) is False
    assert cache.is_rate_limited("1.1.1.1", 2) is False
    assert cache.is_rate_limited("1.1.1.1", 2) is False
    assert cache.is_rate_limited("1.1.1.1", 2) is True
