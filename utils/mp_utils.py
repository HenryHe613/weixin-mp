import os
import time
import requests
import threading
from aiohttp import ClientSession
from utils.log_utils import LOG
from utils.redis_utils import RedisUtils


class MPUtils:
    logger = LOG(level=LOG.DEBUG).logger

    def __init__(self):
        self.APPID = os.getenv("APPID")
        self.APPSECRET = os.getenv("APPSECRET")
        self.TEMPLATE_ID = os.getenv("TEMPLATE_ID")
        self.redis_client = RedisUtils()
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

    def __del__(self):
        try:
            self.logger.info("正在停止access_token刷新线程...")

            self.stop_event.set()  # 使用事件通知线程停止

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
            "appid": self.APPID,
            "secret": self.APPSECRET,
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

    def get_user_list(self):
        url = f"https://api.weixin.qq.com/cgi-bin/user/get"
        params = {"access_token": self.access_token}
        response = requests.get(url, params=params)
        return response.json()

    def send_template_message(self, openid, template_id, data):
        url = f"https://api.weixin.qq.com/cgi-bin/message/template/send"
        params = {"access_token": self.access_token}
        data = {"touser": openid, "template_id": template_id, "data": data}
        response = requests.post(url, json=data, params=params)
        return response.json()

    async def send_message(self, openid, title, ip, date, redirect_url):
        url = "https://api.weixin.qq.com/cgi-bin/message/template/send"
        params = {"access_token": self.access_token}
        data = {
            "touser": openid,
            "template_id": self.TEMPLATE_ID,
            "url": redirect_url,
            "data": {
                "thing18": {"value": title},
                "character_string12": {"value": ip},
                "thing3": {"value": date},
            },
        }
        async with ClientSession() as session:
            async with session.post(url, params=params, json=data) as response:
                result = await response.json()
                return result

    def test(self):
        url = "https://open.weixin.qq.com/connect/oauth2/authorize#wechat_redirect"
        params = {
            "appid": APPID,
            "redirect_uri": "https://api.example.com/mp/login?id=",
            "response_type": "code",
            "scope": "snsapi_userinfo",
            "connect_redirect": 1,
        }
        response = requests.get(url, params=params)
        print(response.status_code)
        print(response.text)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    APPID = os.getenv("APPID")
    APPSECRET = os.getenv("APPSECRET")
    OPENID = os.getenv("OPENID")
    TEMPLATE_ID = os.getenv("TEMPLATE_ID")

    mp_utils = MPUtils()
    print(mp_utils.get_user_list())
