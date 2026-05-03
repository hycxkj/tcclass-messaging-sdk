"""
SDK 客户端模块

提供与消息服务 API 交互的主要客户端类。
"""
from .client_connect import ClientConnection

class MessagingClient:
    """
    消息服务客户端类。

    用于与消息服务 API 交互的主要客户端。
    """
    def __init__(self, host: str, port: int, Authorization: object = None):
        """
        初始化消息服务客户端。

        Args:
            host (str): 消息服务 API 主机地址。
            port (int): 消息服务 API 端口号。
            Authorization (object, optional): 授权对象，用于 API 认证。默认值为 None。
        """
        self.host = host
        self.port = port
        self.Authorization = Authorization
        self.client_conn = ClientConnection(host, port, Authorization)
    
    def connect(self):
        """
        连接到消息服务 API。

        连接成功后，客户端可以使用其他方法与 API 交互。
        """
        try:
            self.client_conn.connect()
        except ConnectionError as e:
            raise MessagingSDKError(f"客户端连接失败: {e}")
        
