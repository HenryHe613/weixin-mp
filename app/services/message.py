# -*- coding: utf-8 -*-
# app/services/message.py

from fastapi import Depends
from datetime import datetime
from aiomysql import Connection
from app.database.mysql import MySQL
from app.database.mongo import MongoDB
from app.services.mp import MPUtils
from app.core.config import settings
from app.core.dependencies import get_mysql, get_mongodb, get_mp


class MessageService:
    def __init__(
        self,
        mysql_conn: Connection = Depends(get_mysql),
        mongodb: MongoDB = Depends(get_mongodb),
        mp: MPUtils = Depends(get_mp),
    ):
        self.mysql_conn = mysql_conn
        self.mongodb = mongodb
        self.mp = mp

    async def send_message(
        self,
        client_ip: str,
        openid: str,
        title: str,
        content: str,
        group: str = None,
    ):
        """核心消息发送逻辑"""
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # MongoDB 操作
        mongo_doc = {
            "openid": openid,
            "title": title,
            "content": content,
            "ip": client_ip,
            "date": time_now,
        }
        mongo_result = await self.mongodb.insert(mongo_doc)

        # 处理群组发送
        if group:
            group_list = await self._get_group_members(openid, group)
            if not group_list:
                return {"msg": "nobody in group"}

            results = []
            for member_openid in group_list:
                result = await self._send_single_message(
                    member_openid,
                    title,
                    client_ip,
                    time_now,
                    mongo_result["inserted_id"],
                )
                results.append(result)
            return {"group_results": results}

        # 单用户发送
        return await self._send_single_message(
            openid,
            title,
            client_ip,
            time_now,
            mongo_result["inserted_id"],
        )

    async def _get_group_members(self, openid: str, group: str) -> list:
        """获取群组成员"""
        return await MySQL.get_group_member(
            conn=self.mysql_conn,
            openid=openid,
            group_name=group,
        )

    async def _send_single_message(
        self,
        openid: str,
        title: str,
        client_ip: str,
        time_now: str,
        mongo_id: str,
    ):
        """发送单个消息"""
        redirect_url = settings.main_path + "/weixin_msg/" + mongo_id
        return await self.mp.send_message(
            openid=openid,
            title=title,
            ip=client_ip,
            date=time_now,
            redirect_url=redirect_url,
        )

    async def get_message(self, message_id: str):
        """消息内容查询逻辑"""
        doc = await self.mongodb.find_one({"_id": message_id})
        if not doc:
            raise ValueError("Message not found")

        # 敏感字段过滤
        doc.pop("openid", None)
        return doc
