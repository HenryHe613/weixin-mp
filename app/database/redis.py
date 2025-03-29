from redis.asyncio import Redis as AsyncRedis
from app.core.config import settings


class Redis:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """异步初始化方法 (需在 FastAPI 启动事件中调用)"""
        if self._initialized:
            return

        self.host = settings.redis_host
        self.port = int(settings.redis_port)
        self.db = int(settings.redis_db)
        # self._password = settings.redis_password

        # 创建异步连接池
        self._redis = AsyncRedis(
            host=self.host,
            port=self.port,
            db=self.db,
            # password=self._password,
            decode_responses=True,
            socket_timeout=40,
            socket_connect_timeout=40,
            retry_on_timeout=True,
            max_connections=100,
        )

        Redis._initialized = True

    async def close(self):
        """关闭连接池 (需在 FastAPI 关闭事件中调用)"""
        await self._redis.close()

    # 以下是异步方法实现
    async def get(self, key):
        return await self._redis.get(key)

    async def set(self, key, value, ex=None):
        return await self._redis.set(key, value, ex=ex)

    async def delete(self, key):
        return await self._redis.delete(key)

    async def keys(self, pattern):
        return await self._redis.keys(pattern)

    async def exists(self, key):
        return await self._redis.exists(key) > 0

    async def incr(self, key, amount=1):
        return await self._redis.incr(key, amount)

    async def sadd(self, key, *values):
        return await self._redis.sadd(key, *values)

    async def sismember(self, key, value):
        return await self._redis.sismember(key, value)

    async def lpush(self, key, *values):
        return await self._redis.lpush(key, *values)

    async def rpush(self, key, *values):
        return await self._redis.rpush(key, *values)

    async def blpop(self, key, timeout=0):
        return await self._redis.blpop(key, timeout)

    async def lpop(self, key):
        return await self._redis.lpop(key)

    async def brpop(self, key, timeout=0):
        return await self._redis.brpop(key, timeout)

    async def llen(self, key):
        return await self._redis.llen(key)

    async def setex(self, key, time, value):
        return await self._redis.setex(key, time, value)

    async def flushdb(self):
        return await self._redis.flushdb()

    async def lrange(self, key, start, end):
        return await self._redis.lrange(key, start, end)

    async def pipeline(self):
        """获取异步管道上下文"""
        return self._redis.pipeline()
