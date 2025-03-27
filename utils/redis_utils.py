import os
import redis
from functools import wraps


class RedisUtils:
    def __init__(self):
        host = os.getenv("REDIS_HOST")
        port = os.getenv("REDIS_PORT")
        db = os.getenv("REDIS_DB")
        password = os.getenv("REDIS_PASSWORD", None)
        unix_socket_path = os.getenv("REDIS_SOCKET_PATH")

        # 连接参数
        connection_kwargs = {
            "db": int(db),
            "password": password,
            "decode_responses": False,  # 保持原始数据类型
            "socket_timeout": 40,
            "socket_connect_timeout": 40,
            "retry_on_timeout": True,
            "max_connections": 100,
        }

        # 优先使用Unix套接字
        if unix_socket_path and os.path.exists(unix_socket_path):
            self.__pool = redis.ConnectionPool(
                unix_socket_path=unix_socket_path, **connection_kwargs
            )
        else:
            # 回退到TCP连接
            self.__pool = redis.ConnectionPool(
                host=host, port=int(port), **connection_kwargs
            )

        self.__redis = redis.Redis(connection_pool=self.__pool)
        self.pipe = self.__redis.pipeline()

    def __del__(self):
        self.__pool.disconnect()
        self.__redis.close()

    # 自动解码装饰器
    def auto_decode(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            result = method(self, *args, **kwargs)
            decode = kwargs.get("decode", False)

            if not decode or result is None:
                return result

            # 处理不同类型的返回值
            if isinstance(result, bytes):
                return result.decode("utf-8")
            elif isinstance(result, list):
                return [
                    item.decode("utf-8") if isinstance(item, bytes) else item
                    for item in result
                ]
            elif isinstance(result, tuple) and len(result) == 2:
                return (
                    (
                        result[0].decode("utf-8")
                        if isinstance(result[0], bytes)
                        else result[0]
                    ),
                    (
                        result[1].decode("utf-8")
                        if isinstance(result[1], bytes)
                        else result[1]
                    ),
                )

            return result

        return wrapper

    @auto_decode
    def get(self, key, decode=False):
        """获取值，可选自动解码"""
        return self.__redis.get(key)

    def set(self, key, value, ex=None):
        """设置值，支持过期时间"""
        return self.__redis.set(key, value, ex=ex)

    def delete(self, key):
        """删除键"""
        return self.__redis.delete(key)

    @auto_decode
    def keys(self, pattern, decode=True):
        """查找匹配的键"""
        result = self.__redis.keys(pattern)
        if decode and result:
            return [key.decode("utf-8") for key in result]
        return result

    def exists(self, key):
        """检查键是否存在"""
        return self.__redis.exists(key) > 0

    def incr(self, key, amount=1):
        """增加值"""
        return self.__redis.incr(key, amount)

    def sadd(self, key, *values):
        """添加到集合"""
        return self.__redis.sadd(key, *values)

    def sismember(self, key, value):
        """检查是否是集合成员"""
        return self.__redis.sismember(key, value)

    def lpush(self, key, *values):
        """左侧推入列表"""
        return self.__redis.lpush(key, *values)

    def rpush(self, key, *values):
        """右侧推入列表"""
        return self.__redis.rpush(key, *values)

    @auto_decode
    def blpop(self, key, timeout=0, decode=True):
        """左侧阻塞弹出，返回(key,value)元组"""
        result = self.__redis.blpop(key, timeout)
        if result and decode:
            return result[0].decode("utf-8"), result[1].decode("utf-8")
        return result

    @auto_decode
    def lpop(self, key, count=1, decode=True):
        """左侧弹出"""
        result = self.__redis.lpop(key, count)
        if decode:
            return [item.decode("utf-8") for item in result]
        return result

    @auto_decode
    def brpop(self, key, timeout=0, decode=True):
        """右侧阻塞弹出，返回(key,value)元组"""
        result = self.__redis.brpop(key, timeout)
        if result and decode:
            return result[0].decode("utf-8"), result[1].decode("utf-8")
        return result

    # llen返回整数，不需要解码
    def llen(self, key):
        """获取列表长度"""
        return self.__redis.llen(key)

    def setex(self, key, time, value):
        """设置带过期时间的值"""
        return self.__redis.setex(key, time, value)

    def flushdb(self):
        """清空当前数据库"""
        return self.__redis.flushdb()

    @property
    def should_stop(self):
        """检查是否应该停止处理"""
        return self.exists("stop_flag")

    def signal_stop(self, timeout=60):
        """发送停止信号"""
        return self.setex("stop_flag", timeout, 1)

    @auto_decode
    def lrange(self, key, index_start, index_end, decode=True):
        """获取列表指定区间的元素"""
        result = self.__redis.lrange(key, index_start, index_end)
        if decode:
            return [item.decode("utf-8") for item in result]
        return result
