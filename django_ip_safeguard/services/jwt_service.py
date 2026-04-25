import datetime as dt
from typing import Optional

import jwt
from django.contrib.auth import get_user_model

from django_ip_safeguard.conf import get_settings


def _utc_ts(seconds: int) -> int:
    return int((dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds)).timestamp())


def create_access_token(user_id: int, username: str) -> str:
    cfg = get_settings()
    payload = {
        "sub": str(user_id),
        "username": username,
        "typ": "access",
        "iat": _utc_ts(0),
        "exp": _utc_ts(cfg.jwt_access_token_ttl_seconds),
    }
    return jwt.encode(payload, cfg.jwt_secret_key, algorithm=cfg.jwt_algorithm)


def create_refresh_token(user_id: int, username: str) -> str:
    cfg = get_settings()
    payload = {
        "sub": str(user_id),
        "username": username,
        "typ": "refresh",
        "iat": _utc_ts(0),
        "exp": _utc_ts(cfg.jwt_refresh_token_ttl_seconds),
    }
    return jwt.encode(payload, cfg.jwt_secret_key, algorithm=cfg.jwt_algorithm)


def decode_token(token: str) -> dict:
    """校验签名与过期时间，仅允许配置的算法。"""
    cfg = get_settings()
    return jwt.decode(
        token,
        cfg.jwt_secret_key,
        algorithms=[cfg.jwt_algorithm],
        options={"require": ["exp", "iat", "typ"]},
    )


def get_user_from_access_token(token: str):
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    User = get_user_model()
    try:
        return User.objects.filter(pk=int(user_id)).first()
    except (TypeError, ValueError):
        return None


def issue_token_pair(user) -> dict:
    access = create_access_token(user.id, user.username)
    refresh = create_refresh_token(user.id, user.username)
    cfg = get_settings()
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": cfg.jwt_access_token_ttl_seconds,
    }


def refresh_access_token(refresh_token: str) -> Optional[dict]:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "refresh":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    User = get_user_model()
    try:
        user = User.objects.filter(pk=int(user_id), is_active=True).first()
    except (TypeError, ValueError):
        return None
    if not user:
        return None
    return {
        "access_token": create_access_token(user.id, user.username),
        "token_type": "Bearer",
        "expires_in": get_settings().jwt_access_token_ttl_seconds,
    }
