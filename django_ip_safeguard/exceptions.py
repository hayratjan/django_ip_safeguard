class ProviderError(Exception):
    """IP 情报 Provider 调用异常。"""


class InvalidClientIpError(Exception):
    """客户端 IP 无效或无法识别。"""


class ImproperlyConfiguredError(Exception):
    """配置错误异常。"""
