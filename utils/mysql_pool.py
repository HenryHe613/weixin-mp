import os
import aiomysql


class MySQLPool:
    _pool = None

    @classmethod
    async def create_pool(cls):
        if not cls._pool:
            cls._pool = await aiomysql.create_pool(
                host=os.getenv("MYSQL_HOST"),
                port=int(os.getenv("MYSQL_PORT", 3306)),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
                db=os.getenv("MYSQL_DATABASE"),
                minsize=int(os.getenv("MYSQL_POOL_MINSIZE", 1)),
                maxsize=int(os.getenv("MYSQL_POOL_MAXSIZE", 10)),
                autocommit=True,
                pool_recycle=3600,  # 连接1小时自动重建
            )
        return cls._pool

    @classmethod
    async def get_connection(cls):
        pool = await cls.create_pool()
        return await pool.acquire()

    @classmethod
    async def release_connection(cls, conn):
        pool = await cls.create_pool()
        if conn:
            await pool.release(conn)

    @classmethod
    async def close_pool(cls):
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
