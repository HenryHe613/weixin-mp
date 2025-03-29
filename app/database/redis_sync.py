import redis
from app.core.config import settings


class Redis:
    _instance = None
    _initialized = False

    def __new__(cls):
        # 如果实例不存在，则创建新实例
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if Redis._initialized:
            return

        self.host = settings.redis_host
        self.port = int(settings.redis_port)
        self.db = int(settings.redis_db)

        # 回退到TCP连接
        self._pool = redis.ConnectionPool(
            host=self.host,
            port=int(self.port),
            db=int(self.db),
            decode_responses=True,
            socket_timeout=40,
            socket_connect_timeout=40,
            retry_on_timeout=True,
            max_connections=100,
        )

        self._redis = redis.Redis(connection_pool=self._pool)
        self.pipe = self._redis.pipeline()

        Redis._initialized = True

    def __del__(self):
        if self._pool:
            self._pool.disconnect()
        if self._redis:
            self._redis.close()

    def get(self, key):
        """获取值，可选自动解码"""
        return self._redis.get(key)

    def set(self, key, value, ex=None):
        """设置值，支持过期时间"""
        return self._redis.set(key, value, ex=ex)

    def delete(self, key):
        """删除键"""
        return self._redis.delete(key)

    def keys(self, pattern):
        """查找匹配的键"""
        result = self._redis.keys(pattern)
        return result

    def exists(self, key):
        """检查键是否存在"""
        return self._redis.exists(key) > 0

    def incr(self, key, amount=1):
        """增加值"""
        return self._redis.incr(key, amount)

    def sadd(self, key, *values):
        """添加到集合"""
        return self._redis.sadd(key, *values)

    def sismember(self, key, value):
        """检查是否是集合成员"""
        return self._redis.sismember(key, value)

    def lpush(self, key, *values):
        """左侧推入列表"""
        return self._redis.lpush(key, *values)

    def rpush(self, key, *values):
        """右侧推入列表"""
        return self._redis.rpush(key, *values)

    def blpop(self, key, timeout=0):
        """左侧阻塞弹出，返回(key,value)元组"""
        result = self._redis.blpop(key, timeout)
        return result

    def lpop(self, key, count=1):
        """左侧弹出"""
        result = self._redis.lpop(key, count)
        return result

    def brpop(self, key, timeout=0):
        """右侧阻塞弹出，返回(key,value)元组"""
        result = self._redis.brpop(key, timeout)
        return result

    # llen返回整数，不需要解码
    def llen(self, key):
        """获取列表长度"""
        return self._redis.llen(key)

    def setex(self, key, time, value):
        """设置带过期时间的值"""
        return self._redis.setex(key, time, value)

    def flushdb(self):
        """清空当前数据库"""
        return self._redis.flushdb()

    def lrange(self, key, index_start, index_end):
        """获取列表指定区间的元素"""
        result = self._redis.lrange(key, index_start, index_end)
        return result
