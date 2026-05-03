"""
SDK 异常模块

定义 SDK 中使用的所有自定义异常类。
"""

from typing import Optional


class MessagingSDKError(Exception):
    """
    SDK 基础异常类。

    所有 SDK 异常的基类。

    Attributes:
        message: 错误信息
    """

    def __init__(self, message: str):
        """
        初始化异常。

        Args:
            message: 错误信息
        """
        self.message = message
        super().__init__(self.message)


class AuthenticationError(MessagingSDKError):
    """
    认证错误。

    当 API 密钥无效或已过期时抛出。

    Example:
        >>> try:
        ...     client.send_message()
        ... except AuthenticationError as e:
        ...     print(f"Authentication failed: {e.message}")
    """

    pass


class APIError(MessagingSDKError):
    """
    API 调用错误。

    当 API 返回错误响应时抛出。

    Attributes:
        message: 错误信息
        status_code: HTTP 状态码

    Example:
        >>> try:
        ...     client.get_message("invalid_id")
        ... except APIError as e:
        ...     print(f"API error {e.status_code}: {e.message}")
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        """
        初始化 API 错误。

        Args:
            message: 错误信息
            status_code: HTTP 状态码
        """
        super().__init__(message)
        self.status_code = status_code


class ValidationError(MessagingSDKError):
    """
    参数验证错误。

    当传入的参数无效时抛出。

    Example:
        >>> try:
        ...     client.send_message(to="", content="Hello")
        ... except ValidationError as e:
        ...     print(f"Invalid parameter: {e.message}")
    """

    pass


class RateLimitError(MessagingSDKError):
    """
    请求频率限制错误。

    当 API 请求频率超过限制时抛出。

    Attributes:
        message: 错误信息
        retry_after: 建议的重试等待时间（秒）

    Example:
        >>> try:
        ...     client.send_message(to="user@example.com", content="Hello")
        ... except RateLimitError as e:
        ...     print(f"Rate limited. Retry after {e.retry_after} seconds")
    """

    def __init__(self, message: str, retry_after: Optional[int] = None):
        """
        初始化频率限制错误。

        Args:
            message: 错误信息
            retry_after: 建议的重试等待时间（秒）
        """
        super().__init__(message)
        self.retry_after = retry_after
