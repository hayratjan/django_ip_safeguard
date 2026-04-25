class ProviderError(Exception):
    """IP 情报 Provider 调用异常。"""


class InvalidClientIpError(Exception):
    """客户端 IP 无效或无法识别。"""
