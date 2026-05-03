"""
WebSocket 客户端模块

类似 JS WebSocket 风格的简洁实现。
"""

import asyncio
import json
import threading
from typing import Any, Callable, Dict, Optional, Union

from websockets.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from .exceptions import MessagingSDKError


class WSClient:
    """
    WebSocket 客户端，类似 JS 风格。

    Example:
        >>> ws = WSClient("wss://example.com/ws")
        >>> ws.onopen = lambda: print("已连接")
        >>> ws.onmessage = lambda msg: print(f"收到: {msg}")
        >>> ws.onerror = lambda err: print(f"错误: {err}")
        >>> ws.onclose = lambda: print("已断开")
        >>> ws.connect()
        >>> ws.send({"type": "chat", "content": "Hello"})
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        ping_interval: Optional[float] = 40,
        ping_timeout: Optional[float] = 20,
    ):
        """
        初始化 WebSocket 客户端。

        Args:
            url: WebSocket 服务器地址
            headers: 自定义 HTTP 头
            ping_interval: 心跳间隔（秒），默认 20 秒，None 表示禁用自动心跳
            ping_timeout: 心跳超时（秒），默认 20 秒，None 表示不检查超时
        """
        self.url = url
        self.headers = headers or {}
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout

        self.onopen: Optional[Callable[[], None]] = None
        self.onmessage: Optional[Callable[[Dict[str, Any]], None]] = None
        self.onerror: Optional[Callable[[Exception], None]] = None
        self.onclose: Optional[Callable[[], None]] = None

        self._ws = None
        self._loop = None
        self._thread = None
        self._running = False
        self._connected = threading.Event()

    @property
    def readyState(self) -> int:
        """
        连接状态 (类似 JS)。

        Returns:
            0: CONNECTING, 1: OPEN, 2: CLOSING, 3: CLOSED
        """
        if self._ws is None:
            return 3 if not self._running else 0
        return 1 if self._connected.is_set() else 0

    def connect(self, timeout: Optional[float] = None) -> bool:
        """
        连接服务器。

        Args:
            timeout: 连接超时时间（秒）

        Returns:
            是否连接成功
        """
        if self._running:
            raise MessagingSDKError("已在运行中")

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        if timeout is not None:
            return self._connected.wait(timeout)
        return True

    def close(self):
        """关闭连接。"""
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._close_ws(), self._loop)
        if self._thread:
            self._thread.join(timeout=3)

    def send(self, data: Union[Dict, str]):
        """
        发送消息。

        Args:
            data: 字典或字符串
        """
        if not self._running or not self._ws:
            raise MessagingSDKError("未连接")

        msg = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else data
        asyncio.run_coroutine_threadsafe(self._ws.send(msg), self._loop)

    def _run_loop(self):
        """运行事件循环。"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main_loop())
        finally:
            self._loop.close()

    async def _main_loop(self):
        """主循环。"""
        try:
            async with ws_connect(
                self.url,
                extra_headers=self.headers,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
            ) as ws:
                self._ws = ws
                self._connected.set()
                if self.onopen:
                    self.onopen()

                async for message in ws:
                    if not self._running:
                        break
                    await self._handle_msg(message)

        except Exception as e:
            if self.onerror:
                self.onerror(e)
        finally:
            self._connected.clear()
            if self.onclose:
                self.onclose()

    async def _handle_msg(self, msg: str):
        """处理消息。"""
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            data = msg

        if self.onmessage:
            self.onmessage(data)

    async def _close_ws(self):
        """关闭 WebSocket。"""
        if self._ws:
            await self._ws.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
