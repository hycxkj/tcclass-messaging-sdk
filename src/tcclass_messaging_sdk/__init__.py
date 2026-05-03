"""
TCClass Messaging SDK

一个用于消息服务的 Python SDK。

示例:
    >>> from tcclass_messaging_sdk import MessagingClient
    >>> client = MessagingClient(api_key="your_api_key")
    >>> client.send_message(to="user@example.com", content="Hello!")
"""

__version__ = "0.1.0"

from .client import MessagingClient
from .exceptions import (
    MessagingSDKError,
    AuthenticationError,
    APIError,
    ValidationError,
    RateLimitError,
)

__all__ = [
    "MessagingClient",
    "MessagingSDKError",
    "AuthenticationError",
    "APIError",
    "ValidationError",
    "RateLimitError",
]
