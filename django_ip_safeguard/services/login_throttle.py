import json
import logging
import time
from typing import Optional, Tuple

from django_ip_safeguard.conf import get_settings

logger = logging.getLogger(__name__)

LOGIN_FAIL_PREFIX = "ip_guard:login_fail:"
LOGIN_LOCK_PREFIX = "ip_guard:login_lock:"

DEFAULT_MAX_FAILURES = 5
DEFAULT_LOCKOUT_SECONDS = 900


def _get_redis():
    from django_ip_safeguard.services.cache import RedisCacheService
    cfg = get_settings()
    return RedisCacheService(cfg.redis_url)


def _fail_key(identifier: str) -> str:
    return f"{LOGIN_FAIL_PREFIX}{identifier}"


def _lock_key(identifier: str) -> str:
    return f"{LOGIN_LOCK_PREFIX}{identifier}"


def check_login_throttle(ip: str, username: str) -> Optional[Tuple[int, int]]:
    try:
        svc = _get_redis()
        client = svc.client
    except Exception:
        return None

    max_failures = DEFAULT_MAX_FAILURES
    lockout_seconds = DEFAULT_LOCKOUT_SECONDS

    for identifier in [ip, f"user:{username}"]:
        lock_key = _lock_key(identifier)
        try:
            ttl = client.ttl(lock_key)
            if ttl and ttl > 0:
                return (ttl, max_failures)
        except Exception:
            pass

    return None


def record_login_failure(ip: str, username: str) -> Optional[int]:
    try:
        svc = _get_redis()
        client = svc.client
    except Exception:
        return None

    max_failures = DEFAULT_MAX_FAILURES
    lockout_seconds = DEFAULT_LOCKOUT_SECONDS

    for identifier in [ip, f"user:{username}"]:
        fail_key = _fail_key(identifier)
        try:
            count = client.incr(fail_key)
            if count == 1:
                client.expire(fail_key, lockout_seconds)
            if count >= max_failures:
                lock_key = _lock_key(identifier)
                client.setex(lock_key, lockout_seconds, str(count))
                client.delete(fail_key)
                return count
        except Exception:
            pass

    return None


def clear_login_failures(ip: str, username: str) -> None:
    try:
        svc = _get_redis()
        client = svc.client
    except Exception:
        return

    for identifier in [ip, f"user:{username}"]:
        try:
            client.delete(_fail_key(identifier))
            client.delete(_lock_key(identifier))
        except Exception:
            pass
