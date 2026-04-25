from django_ip_safeguard.services.cache import RedisCacheService


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.sorted_sets = {}

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

    def pipeline(self):
        return FakePipeline(self)

    def zremrangebyscore(self, key, min_score, max_score):
        if key not in self.sorted_sets:
            return 0
        self.sorted_sets[key] = [
            (member, score)
            for member, score in self.sorted_sets[key]
            if not (min_score <= score <= max_score)
        ]
        return len(self.sorted_sets[key])

    def zadd(self, key, mapping):
        if key not in self.sorted_sets:
            self.sorted_sets[key] = []
        for member, score in mapping.items():
            self.sorted_sets[key].append((member, score))
        return len(self.sorted_sets[key])

    def zcard(self, key):
        return len(self.sorted_sets.get(key, []))


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def zremrangebyscore(self, key, min_score, max_score):
        self.commands.append(("zremrangebyscore", key, min_score, max_score))
        return self

    def zadd(self, key, mapping):
        self.commands.append(("zadd", key, mapping))
        return self

    def zcard(self, key):
        self.commands.append(("zcard", key))
        return self

    def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))
        return self

    def execute(self):
        results = []
        for cmd in self.commands:
            op = cmd[0]
            if op == "zremrangebyscore":
                results.append(self.redis.zremrangebyscore(cmd[1], cmd[2], cmd[3]))
            elif op == "zadd":
                results.append(self.redis.zadd(cmd[1], cmd[2]))
            elif op == "zcard":
                results.append(self.redis.zcard(cmd[1]))
            elif op == "expire":
                results.append(self.redis.expire(cmd[1], cmd[2]))
        self.commands = []
        return results


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
