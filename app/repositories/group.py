# -*- coding: utf-8 -*-
# app/repositories/group.py

import re
from fastapi import Depends
from aiomysql import Connection
from app.core.dependencies import get_mysql



class GroupRepository:
    def __init__(self, conn: Connection = Depends(get_mysql)):
        self.conn = conn

    async def create_group(self, openid: str, group_name: str) -> bool:
        """创建群组的具体实现"""
        if not self._validate_group_name(group_name):
            raise ValueError("群组名格式错误")
            
        async with self.conn.cursor() as cursor:
            # 具体SQL操作
            await cursor.execute(
                "INSERT INTO groups (...) VALUES (...)",
                (openid, group_name)
            )
            return cursor.lastrowid

    @staticmethod
    def _validate_group_name(name: str) -> bool:
        return re.fullmatch(r"^[\w]+$", name) is not None
