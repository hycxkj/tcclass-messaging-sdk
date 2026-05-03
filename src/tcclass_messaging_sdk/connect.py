import asyncio
import threading
from typing import Dict, Optional, Callable, Any

from .websocket_client import WSClient
from .peer import Peer


class ClientConnection:
    """
    消息服务客户端连接类。

    用于与消息服务 API 进行连接和通信。
    """

    def __init__(
        self,
        host: str,
        port: int,
        Authorization: object = None,
        ping_interval: float = 40,
        ping_timeout: float = 20,
    ):
        """
        初始化消息服务客户端连接。

        Args:
            host (str): 消息服务 API 主机地址。
            port (int): 消息服务 API 端口号。
            Authorization (object, optional): 授权对象，用于 API 认证。默认值为 None。
            ping_interval (float): 心跳间隔（秒），默认 40 秒。
            ping_timeout (float): 心跳超时（秒），默认 20 秒。
        """
        self.host = host
        self.port = port
        self.Authorization = Authorization
        self.ws_client = WSClient(
            f"wss://{self.host}:{self.port}/v1/student/ws",
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
        )
        self.peers: Dict[str, Peer] = {}
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._on_p2p_message: Optional[Callable[[str, Any], None]] = None

    def _handle_message(self, msg: Dict):
        """
        内部消息处理器，过滤内部消息后调用 run_command。

        Args:
            msg (Dict): 收到的消息字典。
        """
        msg_type = msg.get("type")
        if msg_type in ("heartbeat", "heartbeat_response", "pong", "ping"):
            return

        self.run_command(msg)

    def connect(self, timeout: float = 10.0):
        """
        连接到消息服务 API。

        连接成功后，客户端可以使用其他方法与 API 交互。

        Args:
            timeout: 认证超时时间（秒），默认 10 秒。

        Raises:
            ConnectionError: 连接或认证失败时抛出。
        """
        auth_event = threading.Event()
        auth_success = [False]
        auth_data = [None]

        def on_auth_response(msg):
            if msg.get("type") == "auth_response":
                auth_data[0] = msg.get("data")
                auth_success[0] = msg.get("success", True)
                auth_event.set()

        try:
            self.ws_client.onmessage = on_auth_response
            self.ws_client.connect()

            self.ws_client.send({"type": "auth", "Authorization": self.Authorization})

            if not auth_event.wait(timeout):
                raise ConnectionError("认证超时")

            if not auth_success[0]:
                raise ConnectionError(f"认证失败: {auth_data[0]}")

            self.ws_client.onmessage = self._handle_message

        except ConnectionError:
            raise
        except Exception as e:
            raise ConnectionError(f"连接失败: {e}")

    def close(self):
        """关闭连接。"""
        self.ws_client.close()
        for peer in self.peers.values():
            asyncio.run_coroutine_threadsafe(peer.close(), self._event_loop)
        self.peers.clear()
        if self._event_loop and self._event_loop.is_running():
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=5)

    def _start_event_loop(self):
        """
        启动 asyncio 事件循环线程。
        """
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        self._event_loop.run_forever()

    def _ensure_event_loop(self):
        """
        确保 asyncio 事件循环已启动。
        """
        if self._loop_thread is None or not self._loop_thread.is_alive():
            self._loop_thread = threading.Thread(target=self._start_event_loop, daemon=True)
            self._loop_thread.start()
            import time
            time.sleep(0.1)

    def send_message(self, message: dict):
        """
        发送消息。

        Args:
            message (dict): 要发送的消息字典。
        """
        self.ws_client.send(message)

    def run_command(self, msg: Dict):
        """
        处理服务端消息，子类可重写此方法实现自定义逻辑。

        Args:
            msg (Dict): 收到的消息字典。
        """
        type = msg.get("type")

        match type:
            case "p2p-teacher":
                self._handle_p2p_message(msg)
            case "classroom-id-set":
                pass
            case "classroom-id-get":
                pass
            case _:
                pass

    def _handle_p2p_message(self, msg: Dict):
        """
        处理 P2P 消息。

        Args:
            msg (Dict): P2P 消息字典，包含 data 字段。
        """
        data = msg.get("data", {})
        peer_id = data.get("peer_id", "default")
        msg_type = data.get("type")
        rtcdata = data.get("rtcdata", {})

        self._ensure_event_loop()

        if peer_id not in self.peers:
            on_message = None
            if self._on_p2p_message:
                def create_callback(pid):
                    def callback(message):
                        self._on_p2p_message(pid, message)
                    return callback
                on_message = create_callback(peer_id)
            self.peers[peer_id] = Peer(on_message=on_message)

        peer = self.peers[peer_id]

        if msg_type == "offer":
            asyncio.run_coroutine_threadsafe(
                self._handle_offer(peer, peer_id, rtcdata),
                self._event_loop
            )
        elif msg_type == "answer":
            asyncio.run_coroutine_threadsafe(
                self._handle_answer(peer, rtcdata),
                self._event_loop
            )
        elif msg_type == "ice":
            asyncio.run_coroutine_threadsafe(
                peer.add_ice_candidate(rtcdata),
                self._event_loop
            )

    async def _handle_offer(self, peer: Peer, peer_id: str, rtcdata: Dict):
        """
        处理 SDP offer。

        Args:
            peer (Peer): Peer 实例。
            peer_id (str): 对等端 ID。
            rtcdata (Dict): SDP 数据。
        """
        await peer.set_remote_description(rtcdata)
        answer = await peer.create_answer()
        self.ws_client.send({
            "type": "p2p-student",
            "data": {
                "peer_id": peer_id,
                "Authorization": self.Authorization,
                "type": "answer",
                "rtcdata": answer
            }
        })
        for candidate in peer.get_ice_candidates():
            self.ws_client.send({
                "type": "p2p-student",
                "data": {
                    "peer_id": peer_id,
                    "Authorization": self.Authorization,
                    "type": "ice",
                    "rtcdata": candidate
                }
            })

    async def _handle_answer(self, peer: Peer, rtcdata: Dict):
        """
        处理 SDP answer。

        Args:
            peer (Peer): Peer 实例。
            rtcdata (Dict): SDP 数据。
        """
        await peer.set_remote_description(rtcdata)

    def create_p2p_connection(self, peer_id: str, on_message: Optional[Callable[[Any], None]] = None) -> Peer:
        """
        创建 P2P 连接。

        Args:
            peer_id (str): 对等端 ID。
            on_message (Callable[[Any], None], optional): 消息回调函数。

        Returns:
            Peer: 创建的 Peer 实例。
        """
        self._ensure_event_loop()

        if peer_id in self.peers:
            return self.peers[peer_id]

        peer = Peer(on_message=on_message)
        self.peers[peer_id] = peer

        async def create_and_send_offer():
            await peer.create_data_channel()
            offer = await peer.create_offer()
            self.ws_client.send({
                "type": "p2p-student",
                "data": {
                    "peer_id": peer_id,
                    "Authorization": self.Authorization,
                    "type": "offer",
                    "rtcdata": offer
                }
            })
            for candidate in peer.get_ice_candidates():
                self.ws_client.send({
                    "type": "p2p-student",
                    "Authorization": self.Authorization,
                    "data": {
                        "peer_id": peer_id,
                        "type": "ice",
                        "rtcdata": candidate
                    }
                })

        asyncio.run_coroutine_threadsafe(create_and_send_offer(), self._event_loop)
        return peer

    def set_on_p2p_message(self, callback: Callable[[str, Any], None]):
        """
        设置 P2P 消息回调函数。

        Args:
            callback (Callable[[str, Any], None]): 回调函数，接收 peer_id 和 message 参数。
        """
        self._on_p2p_message = callback

