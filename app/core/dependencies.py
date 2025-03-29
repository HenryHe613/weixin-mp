from aiomysql import Connection
from fastapi import Depends, Request
from app.database.mysql import MySQL
from app.database.mongo import MongoDB
from app.database.redis import Redis
from app.services.mp import MPUtils
from typing import AsyncGenerator


async def get_mysql() -> AsyncGenerator[Connection, None]:
    conn = await MySQL.get_connection()
    try:
        yield conn
    finally:
        await MySQL.release_connection(conn)


async def get_mongodb(request: Request) -> MongoDB:
    """获取MongoDB操作实例的依赖项"""
    client = request.app.state.mongodb_client
    return MongoDB(client=client)


async def get_redis(request: Request) -> Redis:
    """获取Redis操作实例的依赖项"""
    return request.app.state.redis_client


async def get_mp(request: Request) -> MPUtils:
    """获取微信公众号操作实例的依赖项"""
    return request.app.state.mp_instance
