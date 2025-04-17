# -*- coding: utf-8 -*-
# app/services/wechat.py

import re
import time
from fastapi import Depends
from aiomysql import Connection
from xml.etree import ElementTree as ET
from app.core.config import settings
from app.core.dependencies import get_mysql
from app.database.mysql import MySQL


class WechatService:

    HELP_MESSAGE = (
        "/id - 获取您的 OpenID\n" "/group - 群组操作\n" "/help - 获取帮助信息"
    )

    def __init__(
        self,
        mysql_conn: Connection = Depends(get_mysql),
        # repo: GroupRepository = Depends(GroupRepository),
        # user_repo: UserRepository = Depends(UserRepository),
    ):
        self.mysql_conn = mysql_conn
        # self.repo = repo
        # self.user_repo = user_repo
        pass

    async def process_text_message(self, from_user: str, content: str) -> str:
        """处理文本消息业务逻辑"""
        if content == "/id":
            return await self._handle_get_id(from_user)
        elif content.startswith("/group"):
            return await self._handle_group_operations(from_user, content)
        elif content == "/help":
            return self.HELP_MESSAGE
        return "未知指令，请输入/help查看帮助"

    async def _handle_group_operations(self, openid: str, content: str) -> str:
        """处理群组相关操作"""
        # 命令解析交给独立方法
        command, *args = self._parse_group_command(content)
        print(command, *args)

        # 使用策略模式处理不同命令
        handlers = {
            "create": self._create_group,
            "delete": self._delete_group,
            "join": self._join_group,
            "leave": self._leave_group,
            "list": self._list_groups,
        }

        if command not in handlers:
            return "无效的群组命令"

        return await handlers[command](openid, *args)

    def _parse_group_command(self, content: str) -> tuple:
        """解析群组命令专用方法"""
        parts = content.split()
        if len(parts) < 2:
            return ("invalid",)
        return parts[1], parts[2:] if len(parts) > 2 else []

    def parse_message_body(self, body: bytes):
        """解析微信服务器返回的用户消息"""
        root = ET.fromstring(body.decode("utf-8"))

        # 解析 XML 消息
        msg_type = root.find("MsgType").text
        from_user = root.find("FromUserName").text  # 用户的 OpenID
        to_user = root.find("ToUserName").text
        content = root.find("Content").text.strip()

        return msg_type, from_user, to_user, content

    def generate_xml_response(self, to_user: str, from_user: str, content: str) -> str:
        # 生成微信要求的 XML 响应
        return f"""<xml>
            <ToUserName><![CDATA[{from_user}]]></ToUserName>
            <FromUserName><![CDATA[{to_user}]]></FromUserName>
            <CreateTime>{int(time.time())}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[{content}]]></Content>
        </xml>"""

    async def _create_group(self, openid: str, group_name: str) -> bool:
        # 创建群组
        if not re.fullmatch(r"^[\w]+$", group_name):
            raise ValueError("群组名只能包含字母、数字和下划线")
        try:
            if await MySQL.create_group(
                conn=self.mysql_conn,
                openid=openid,
                group_name=group_name,
            ):
                return True
            else:
                return False
        except Exception as e:
            return False

    async def _delete_group(self, openid: str, group_name: str) -> bool:
        # 删除群组
        try:
            if await MySQL.delete_group(
                conn=self.mysql_conn,
                openid=openid,
                group_name=group_name,
            ):
                return True
            else:
                return False
        except Exception as e:
            return False
    
    async def _join_group(self, openid: str, group_name: str) -> bool:
        # 加入群组, 对应命令 /group join <name>
        try:
            if await MySQL.join_group(
                conn=self.mysql_conn,
                openid=openid,
                group_name=group_name,
            ):
                return True
            else:
                return False
        except Exception as e:
            return False
    
    async def _leave_group(self, openid: str, group_name: str) -> bool:
        # 离开群组, 对应命令 /group leave <name>
        try:
            if await MySQL.leave_group(
                conn=self.mysql_conn,
                openid=openid,
                group_name=group_name,
            ):
                return True
            else:
                return False
        except Exception as e:
            return False
    
    async def _list_groups(self, openid: str, *args) -> str:
        try:
            group_list = await MySQL.get_info(conn=self.mysql_conn, openid=openid,)
        except Exception as e:
            return f"获取群组信息失败：{e}"
        reply = ""
        if len(group_list["owner"]) > 0:
            reply += "创建的群组：\n" + "\n".join(group_list["owner"]) + "\n"
        if len(group_list["member"]) > 0:
            reply += "加入的群组：\n" + "\n".join(group_list["member"]) + "\n"
        if not reply:
            reply = "您还没有创建或加入任何群组"
        return reply
