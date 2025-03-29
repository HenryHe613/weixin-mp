import time
import requests
import threading
from aiohttp import ClientSession
from app.core.logger import LOG
from app.core.config import settings
from app.database.redis_sync import Redis


class MPUtils:
    logger = LOG(level=LOG.DEBUG).logger
    _instance = None
    _initialized = False
    stop_event = threading.Event()

    def __new__(cls):
        # 如果实例不存在，则创建新实例
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.redis_client = Redis()
        self.access_token = (
            self.redis_client.get("access_token", decode=True)
            if self.redis_client.exists("access_token")
            else None
        )
        self.stop_event = threading.Event()  # 使用本地事件
        self.thread_refresh_access_token = threading.Thread(
            target=self.refresh_access_token, daemon=True
        )
        self.thread_refresh_access_token.start()
        self.logger.info(f"access_token: {self.access_token}")
        
        self._initialized = True

    def __del__(self):
        try:
            self.logger.info("正在停止access_token刷新线程...")

            # 使用事件通知线程停止
            self.stop_event.set()

            # 设置join超时，防止永久阻塞
            self.thread_refresh_access_token.join(timeout=2.0)

            if self.thread_refresh_access_token.is_alive():
                self.logger.warning("线程未能在超时时间内完成，但程序会继续退出")
            else:
                self.logger.info("access_token刷新线程已成功停止")
        except Exception as e:
            self.logger.error(f"停止线程时出错: {e}")

    def get_access_token(self) -> None:
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": settings.appid,
            "secret": settings.appsecret,
        }
        response = requests.get(url, params=params)
        self.access_token = response.json()["access_token"]

    def refresh_access_token(self):
        while not self.stop_event.is_set():
            if not self.redis_client.exists("access_token_valid"):
                self.get_access_token()
                self.redis_client.set("access_token", self.access_token, 720)
                self.redis_client.set("access_token_valid", 1, 700)
                self.logger.info("刷新access_token成功")
            else:
                time.sleep(1)

    async def send_message(self, openid, title, ip, date, redirect_url):
        url = "https://api.weixin.qq.com/cgi-bin/message/template/send"
        params = {"access_token": self.access_token}
        data = {
            "touser": openid,
            "template_id": settings.template_id,
            "url": redirect_url,
            "data": {
                "thing18": {"value": title},
                "character_string12": {"value": ip},
                "thing3": {"value": date},
            },
        }
        async with ClientSession() as session:
            async with session.post(url, params=params, json=data) as response:
                return await response.json()


if __name__ == "__main__":
    pass
