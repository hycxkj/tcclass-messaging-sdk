import asyncio
from typing import Callable, Optional, Dict, Any
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.signaling import object_from_string, object_to_string


class Peer:
    """
    P2P 通信连接类，基于 WebRTC 实现。

    用于建立和管理 WebRTC 对等连接，支持数据通道通信。
    """

    def __init__(self, on_message: Optional[Callable[[Any], None]] = None):
        """
        初始化 Peer 实例。

        Args:
            on_message (Callable[[Any], None], optional): 消息回调函数，接收到消息时调用。
        """
        self.pc = RTCPeerConnection()
        self.on_message = on_message
        self.data_channel = None
        self._ice_candidates: list[RTCIceCandidate] = []
        self._is_closed = False

        self._setup_pc_callbacks()

    def _setup_pc_callbacks(self):
        """
        设置 RTCPeerConnection 的回调函数。
        """
        @self.pc.on("icecandidate")
        def on_icecandidate(candidate: RTCIceCandidate):
            if candidate:
                self._ice_candidates.append(candidate)

        @self.pc.on("datachannel")
        def on_datachannel(channel):
            self.data_channel = channel
            self._setup_data_channel_callbacks()

    def _setup_data_channel_callbacks(self):
        """
        设置数据通道的回调函数。
        """
        if not self.data_channel:
            return

        @self.data_channel.on("message")
        def on_message(message):
            if self.on_message:
                self.on_message(message)

    async def create_data_channel(self, label: str = "data") -> None:
        """
        创建数据通道。

        Args:
            label (str): 数据通道标签，默认为 "data"。
        """
        self.data_channel = self.pc.createDataChannel(label)
        self._setup_data_channel_callbacks()

    async def create_offer(self) -> Dict[str, Any]:
        """
        创建 SDP offer。

        Returns:
            Dict[str, Any]: 包含 type 和 sdp 的字典。
        """
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        return {"type": self.pc.localDescription.type, "sdp": self.pc.localDescription.sdp}

    async def create_answer(self) -> Dict[str, Any]:
        """
        创建 SDP answer。

        Returns:
            Dict[str, Any]: 包含 type 和 sdp 的字典。
        """
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        return {"type": self.pc.localDescription.type, "sdp": self.pc.localDescription.sdp}

    async def set_remote_description(self, sdp_data: Dict[str, Any]) -> None:
        """
        设置远端 SDP 描述。

        Args:
            sdp_data (Dict[str, Any]): 包含 type 和 sdp 的字典。
        """
        description = RTCSessionDescription(sdp=sdp_data["sdp"], sdpType=sdp_data["type"])
        await self.pc.setRemoteDescription(description)

    async def add_ice_candidate(self, candidate_data: Dict[str, Any]) -> None:
        """
        添加 ICE candidate。

        Args:
            candidate_data (Dict[str, Any]): ICE candidate 数据。
        """
        candidate_str = candidate_data.get("candidate", "")
        if candidate_str:
            candidate = object_from_string(candidate_str)
            await self.pc.addIceCandidate(candidate)

    def get_ice_candidates(self) -> list[Dict[str, Any]]:
        """
        获取已收集的 ICE candidates。

        Returns:
            list[Dict[str, Any]]: ICE candidate 列表。
        """
        candidates = []
        for candidate in self._ice_candidates:
            candidate_str = object_to_string(candidate)
            candidates.append({
                "candidate": candidate_str,
                "sdpMid": candidate.sdpMid,
                "sdpMLineIndex": candidate.sdpMLineIndex
            })
        return candidates

    def send_message(self, message: Any) -> None:
        """
        通过数据通道发送消息。

        Args:
            message (Any): 要发送的消息。

        Raises:
            RuntimeError: 数据通道未建立时抛出。
        """
        if not self.data_channel:
            raise RuntimeError("数据通道未建立")
        self.data_channel.send(message)

    async def close(self) -> None:
        """
        关闭连接。
        """
        if self._is_closed:
            return
        self._is_closed = True
        await self.pc.close()

    @property
    def connection_state(self) -> str:
        """
        获取连接状态。

        Returns:
            str: 连接状态。
        """
        return self.pc.connectionState

    @property
    def ice_connection_state(self) -> str:
        """
        获取 ICE 连接状态。

        Returns:
            str: ICE 连接状态。
        """
        return self.pc.iceConnectionState
