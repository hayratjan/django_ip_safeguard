from django_ip_safeguard.services.cache import RedisCacheService


def ban_ip(cache_service: RedisCacheService, ip: str, reason: str, ban_ttl: int) -> None:
    """封禁指定 IP。"""

    cache_service.set_ban(ip=ip, reason=reason, ttl=ban_ttl)
