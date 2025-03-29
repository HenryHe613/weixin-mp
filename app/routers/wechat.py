import re
import time
import hashlib
from fastapi import APIRouter, Depends, Request, Response
from xml.etree import ElementTree as ET
from aiomysql import Connection
from app.core.config import settings
from app.core.dependencies import get_mysql
from app.database.mysql import MySQL

router = APIRouter()


@router.get(settings.main_path)
async def verify_server(request: Request):
    # 验证微信服务器有效性（GET 请求）
    signature = request.query_params.get("signature", "")
    timestamp = request.query_params.get("timestamp", "")
    nonce = request.query_params.get("nonce", "")
    echostr = request.query_params.get("echostr", "")

    # 计算签名
    params = sorted([settings.verify_token, timestamp, nonce])
    sign_str = "".join(params)
    hash_str = hashlib.sha1(sign_str.encode()).hexdigest()

    if hash_str == signature:
        return Response(content=echostr)
    else:
        return Response(content="Verification Failed", status_code=403)


@router.post(settings.main_path)
async def handle_message(
    request: Request,
    conn: Connection = Depends(get_mysql),
):
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
            try:
                await MySQL.create_user(
                    conn=conn,
                    openid=from_user,
                    nickname=from_user,
                )
            except Exception as e:
                reply = f"创建用户失败：{e}"

        elif content == "/help":
            # 返回帮助信息
            reply = (
                "/id - 获取您的 OpenID\n" "/group - 群组操作\n" "/help - 获取帮助信息"
            )
        elif len(content_block) and content_block[0] == "/group":
            if len(content_block) == 1:
                # 返回group的操作提示, 对应命令 /group
                reply = (
                    "/group list - 列出所有群组\n"
                    "/group create [name] - 创建群组\n"
                    "/group delete [name] - 删除群组\n"
                    "/group join [name] - 加入群组\n"
                    "/group leave [name] - 离开群组\n"
                )
            elif len(content_block) == 3 and content_block[1] == "create":
                # 创建群组, 对应命令 /group create <name>
                group_name = content_block[2]
                if re.fullmatch(r"^[\w]+$", group_name):
                    # 群组名只能包含字母、数字和下划线
                    try:
                        if await MySQL.create_group(
                            conn=conn,
                            openid=from_user,
                            name=group_name,
                        ):
                            reply = f"群组 {group_name} 创建成功"
                        else:
                            reply = f"群组 {group_name} 创建失败"
                    except Exception as e:
                        reply = f"创建群组失败：{e}"
                else:
                    reply = "群组名只能包含字母、数字和下划线"
            elif len(content_block) == 3 and content_block[1] == "delete":
                # 删除群组, 对应命令 /group delete <name>
                group_name = content_block[2]
                try:
                    if await MySQL.delete_group(
                        conn=conn,
                        openid=from_user,
                        group_name=group_name,
                    ):
                        reply = f"成功删除群组 {group_name}"
                    else:
                        reply = f"群组 {group_name} 删除失败，请检查是否是群组创建者"
                except Exception as e:
                    reply = f"删除群组失败：{e}"
            elif len(content_block) == 3 and content_block[1] == "join":
                # 加入群组, 对应命令 /group join <name>
                group_name = content_block[2]
                try:
                    if await MySQL.join_group(
                        conn=conn,
                        openid=from_user,
                        group_name=group_name,
                    ):
                        reply = f"成功加入群组 {group_name}"
                    else:
                        reply = f"群组 {group_name} 不存在/已加入"
                except Exception as e:
                    reply = f"加入群组失败：{e}"
            elif len(content_block) == 3 and content_block[1] == "leave":
                # 离开群组, 对应命令 /group leave <name>
                group_name = content_block[2]
                try:
                    if await MySQL.leave_group(
                        conn=conn,
                        openid=from_user,
                        group_name=group_name,
                    ):
                        reply = f"成功退出群组 {group_name}（有没有种可能，根本没有这个群组，或你没有加入过）"
                    else:
                        reply = f"退出群组 {group_name} 失败，请检查是否已加入"
                except Exception as e:
                    reply = f"退出群组失败：{e}"
            elif len(content_block) == 2 and content_block[1] == "list":
                # 列出所有群组, 对应命令 /group list
                group_list = await MySQL.get_info(conn=conn, openid=from_user)
                reply = ""
                if len(group_list["owner"]) > 0:
                    reply += "创建的群组：\n" + "\n".join(group_list["owner"]) + "\n"
                if len(group_list["member"]) > 0:
                    reply += "加入的群组：\n" + "\n".join(group_list["member"]) + "\n"
                if not reply:
                    reply = "您还没有创建或加入任何群组"

        if "reply" in locals() and type(reply) == str and len(reply):
            xml_response = generate_xml(to_user, from_user, reply)
            return Response(content=xml_response, media_type="application/xml")

    # 默认返回 success（微信要求）
    return Response(content="success")
