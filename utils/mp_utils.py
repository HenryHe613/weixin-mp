import time
import requests
import threading
from redis_utils import RedisUtils
from log_utils import LOG

class MPUtils:
    def __init__(self):
        self.logger = LOG(level=LOG.DEBUG).logger
        self.redis_client = RedisUtils()
        self.access_token = (
            self.redis_client.get("access_token", decode=True)
            if self.redis_client.exists("access_token")
            else None
        )
        # 启用线程，刷新access_token
        self.redis_client.set("thread_refresh_access_token", 1)
        self.thread_refresh_access_token = threading.Thread(
            target=self.refresh_access_token
        )
        self.thread_refresh_access_token.start()

    def __del__(self):
        self.logger.info("清除access_token刷新线程")
        self.redis_client.delete("thread_refresh_access_token")
        self.thread_refresh_access_token.join()
        self.logger.info("清除access_token刷新线程 完成")

    def get_access_token(self) -> None:
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": APPID,
            "secret": APPSECRET,
        }
        response = requests.get(url, params=params)
        self.access_token = response.json()["access_token"]

    def refresh_access_token(self):
        if not self.redis_client.exists("thread_refresh_access_token"):
            return
        elif not self.redis_client.exists("access_token_valid"):
            self.get_access_token()
            self.redis_client.set("access_token", self.access_token)
            self.redis_client.set("access_token_valid", 1, 700)
            self.logger.info("刷新access_token成功")
        else:
            time.sleep(1)

    def get_user_list(self):
        url = f"https://api.weixin.qq.com/cgi-bin/user/get?access_token={self.access_token}"
        response = requests.get(url)
        return response.json()

    def send_template_message(self, openid, template_id, data):
        url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={self.access_token}"
        data = {"touser": openid, "template_id": template_id, "data": data}
        response = requests.post(url, json=data)
        return response.json()

    def send_message(self, openid, title, ip, date, redirect_url):
        url = "https://api.weixin.qq.com/cgi-bin/message/template/send"
        params = {"access_token": self.access_token}
        data = {
            "touser": OPENID,
            "template_id": TEMPLATE_ID,
            "url": redirect_url,
            "data": {
                "thing18": {"value": "你好"},
                "character_string12": {"value": "8.8.8.8"},
                "thing3": {"value": "2025-03-10"},
            },
        }
        response = requests.post(url, params=params, json=data)
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
    time.sleep(10)
