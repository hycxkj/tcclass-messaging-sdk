import requests
import json
import time
import hashlib
import hmac


class Bind:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.url = f"http://{self.host}:{self.port}/v1/student/bind"
        self.session = requests.Session()

    def get_bind_code(self, classroom_id: str = None, Authorization: object = None):
        """
        绑定教室和学生

        Args:
            classroom_id: 教室ID
            Authorization: 授权对象，需包含 key 和 token 属性

        Returns:
            requests.Response: HTTP响应对象

        Raises:
            ValueError: 当参数为空时抛出
        """
        if not classroom_id:
            raise ValueError("教室ID不能为空，请走注册流程")
        if not Authorization:
            raise ValueError("Authorization 不能为空")
        
        timestamp = int(time.time())
        data = {"c": classroom_id, "t": timestamp}

        hmac_digest = hmac.new(
            Authorization.key.encode() if isinstance(Authorization.key, str) else Authorization.key,
            json.dumps(data, ensure_ascii=False).encode(),
            hashlib.sha256
        ).hexdigest()
        token = Authorization.token

        payload = {"c": classroom_id, "t": token, "k": timestamp, "h": hmac_digest}
        
        res = self.session.post(self.url + "/qr/" + classroom_id, json=payload)
        if res.status_code != 200:
            raise ValueError(f"绑定教室失败，状态码: {res.status_code}, 响应内容: {res.text}")
        
        return res # 教师扫描 /v1/teacher/bind/{teacher_id} (classroom_id, code,teacher_id, token, key, timestamp, hmac)
