import os
import re
import time
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from utils.mp_utils import MPUtils
from utils.mysql_utils import MysqlUtils
from utils.redis_utils import RedisUtils
from utils.mongo_utils import MongoUtils
import xml.etree.ElementTree as ET
from fastapi import FastAPI, Request, Response

load_dotenv()

app = FastAPI()
mysql_client = MysqlUtils()
redis_client = RedisUtils()
mongo_client = MongoUtils()
mp = MPUtils()

# 微信公众平台配置
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
DOMAIN = os.getenv("DOMAIN")
MAIN_PATH = os.getenv("MAIN_PATH")


@app.get(MAIN_PATH)
async def verify_server(request: Request):
    # 验证微信服务器有效性（GET 请求）
    signature = request.query_params.get("signature", "")
    timestamp = request.query_params.get("timestamp", "")
    nonce = request.query_params.get("nonce", "")
    echostr = request.query_params.get("echostr", "")

    # 计算签名
    params = sorted([VERIFY_TOKEN, timestamp, nonce])
    sign_str = "".join(params)
    hash_str = hashlib.sha1(sign_str.encode()).hexdigest()

    if hash_str == signature:
        return Response(content=echostr)
    else:
        return Response(content="Verification Failed", status_code=403)


@app.post(MAIN_PATH)
async def handle_message(request: Request):
    def generate_xml(to_user: str, from_user: str, content: str) -> str:
        # 生成微信要求的 XML 响应
        return f"""<xml>
            <ToUserName><![CDATA[{from_user}]]></ToUserName>
            <FromUserName><![CDATA[{to_user}]]></FromUserName>
            <CreateTime>{int(time.time())}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[{content}]]></Content>
        </xml>"""
    
    # 处理用户消息（POST 请求）
    body = await request.body()
    root = ET.fromstring(body.decode("utf-8"))

    # 解析 XML 消息
    msg_type = root.find("MsgType").text
    from_user = root.find("FromUserName").text  # 用户的 OpenID
    to_user = root.find("ToUserName").text

    if msg_type == "text":
        content = root.find("Content").text.strip()
        content_block = content.split(" ")
        if content == "/id":
            # 返回 OpenID
            reply = f"您的 OpenID 是：{from_user}"
        elif content == "/help":
            # 返回帮助信息
            reply = (
                "/id - 获取您的 OpenID\n" "/group - 群组操作\n" "/help - 获取帮助信息"
            )
        elif len(content_block) and content_block[0] == "/group":
            if len(content_block) == 1:
                # 返回group的操作提示
                reply = "/group create [name] - 创建群组\n" "/group join [name] - 加入群组"
            elif len(content_block) == 3 and content_block[1] == "create":
                # 创建群组
                group_name = content_block[2]
                if re.fullmatch(r'^[\w]+$', group_name):
                    # 群组名只能包含字母、数字和下划线
                    try:
                        mysql_client.create_group(name=group_name, owner_openid=from_user)
                        reply = f"群组 {group_name} 创建成功"
                    except Exception as e:
                        reply = f"创建群组失败：{e}"
            elif len(content_block) == 3 and content_block[1] == "join":
                # 加入群组
                group_name = content_block[2]
                try:
                    mysql_client.join_group(openid=from_user, group_name=group_name)
                    reply = f"成功加入群组 {group_name}"
                except Exception as e:
                    reply = f"加入群组失败：{e}" 
        if 'reply' in locals() and type(reply) == str and len(reply):
            xml_response = generate_xml(to_user, from_user, reply)
            return Response(content=xml_response, media_type="application/xml")

    # 默认返回 success（微信要求）
    return Response(content="success")


@app.post(MAIN_PATH + "/send")
async def send_message(request: Request):
    # 处理模板消息推送（POST 请求）
    client_ip = request.client.host
    body = await request.body()
    body = json.loads(body)
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    required_keys = {"openid", "title", "content"}
    if not required_keys.issubset(body.keys()):
        missing_keys = required_keys - body.keys()
        return Response(
            content=json.dumps({"code": 400, "msg": "Missing parameters."}),
            status_code=400,
            media_type="application/json",
        )
    mongo_result = mongo_client.insert(
        {
            "openid": body["openid"],
            "title": body["title"],
            "content": body["content"],
            "ip": client_ip,
            "date": time_now,
        }
    )
    print(mongo_result)
    result = await mp.send_message(
        openid=body["openid"],
        title=body["title"],
        ip=client_ip,
        date=time_now,
        redirect_url=DOMAIN + "/weixin_msg/"
        + str(mongo_result.inserted_id),
    )
    return Response(content=json.dumps(result), media_type="application/json")


@app.get(MAIN_PATH + "/message")
async def get_message(id: str):
    # 获取推送详细信息
    result = mongo_client.find_one({"_id": id})
    del result["openid"]
    return Response(content=json.dumps(result), media_type="application/json")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("WEB_PORT", 80)))
