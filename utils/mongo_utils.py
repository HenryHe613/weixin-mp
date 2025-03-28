import os
from typing import Union, Dict, Any, List, Optional
from pymongo import MongoClient, UpdateOne
from pymongo.cursor import Cursor
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection


class MongoUtils:
    UpdateOne = UpdateOne

    def __init__(
        self,
        host: str = None,
        port: Union[int, str] = None,
        username: str = None,
        password: str = None,
        database: str = None,
        collection: str = None,
    ) -> None:
        """
        初始化MongoDB工具类，建立数据库连接并配置集合。

        该构造函数会尝试从参数获取连接信息，如果参数为None则从环境变量读取，
        最后使用默认值。成功初始化后将创建MongoDB客户端连接并选择指定的数据库和集合。

        Args:
            host (str, optional): MongoDB主机地址，默认从环境变量MONGO_HOST获取，若无则为127.0.0.1
            port (Union[int, str], optional): MongoDB端口号，默认从环境变量MONGO_PORT获取，若无则为27017
            username (str, optional): MongoDB用户名，默认从环境变量MONGO_USERNAME获取，若无则为root
            password (str, optional): MongoDB密码，默认从环境变量MONGO_PASSWORD获取，若无则为root
            database (str, optional): 数据库名称，默认从环境变量MONGO_DATABASE获取
            collection (str, optional): 集合名称，默认从环境变量MONGO_COLLECTION获取

        Raises:
            pymongo.errors.ConnectionFailure: 当无法连接到MongoDB服务器时抛出
            pymongo.errors.ServerSelectionTimeoutError: 当服务器选择超时时抛出
            pymongo.errors.InvalidName: 当数据库或集合名称无效时抛出
        """

        self.username = username if username else os.getenv("MONGO_USERNAME", "root")
        self._password = password if password else os.getenv("MONGO_PASSWORD", "root")
        self.host = host if host else os.getenv("MONGO_HOST", "127.0.0.1")
        self.port = int(port) if port else int(os.getenv("MONGO_PORT", 27017))
        self.database_name = database if database else os.getenv("MONGO_DATABASE")
        self.collection_name = (
            collection if collection else os.getenv("MONGO_COLLECTION")
        )

        self._client = MongoClient(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self._password,
        )
        self._database = self._client[self.database_name]
        self._collection = self._database[self.collection_name]

    def __del__(self) -> None:
        """
        析构函数，负责在对象被销毁时关闭数据库连接和游标
        这确保了无论如何退出程序，都能正确释放数据库资源，防止连接泄漏
        """
        self._client.close()

    def insert(self, data: dict) -> dict:
        """
        将提供的数据插入MongoDB集合中。
        Args:
            data (dict): 要插入的数据。
        Returns:
            dict: 插入操作的结果。
        """
        result = self._collection.insert_one(data)
        return result

    def update(self, query: dict, data: dict) -> dict:
        """
        根据提供的查询条件更新MongoDB集合中的文档。
        Args:
            query (dict): 用于匹配要更新的文档的查询条件。
            data (dict): 用于更新匹配文档的数据。
        Returns:
            dict: 更新操作的结果。
        """
        data = {"$set": data}
        result = self._collection.update_one(filter=query, update=data, upsert=True)
        return result

    def bulk_write(self, operations: list) -> dict:
        """
        根据提供的查询条件更新MongoDB集合中的文档。
        Args:
            operations (list): 用于更新文档的操作列表。
        Returns:
            dict: 更新操作的结果。
        """
        result = self._collection.bulk_write(operations)
        return result

    def find(self, query: dict, batch_size: int = 100) -> Cursor:
        """
        根据提供的查询条件从MongoDB集合中检索文档。
        Args:
            query (dict): 用于匹配要检索的文档的查询条件。
        Returns:
            Cursor: 匹配查询条件的文档迭代器。
        """

        cursor = self._collection.find(query).batch_size(batch_size)
        return cursor

    def find_one(self, query: dict) -> dict:
        """
        根据提供的查询条件从MongoDB集合中检索第一个符合的文档。
        Args:
            query (dict): 用于匹配要检索的文档的查询条件。
        Returns:
            dict: 匹配查询条件的文档。
        """
        if "_id" in query:
            query["_id"] = ObjectId(query["_id"])
        result = self._collection.find_one(query)
        del result["_id"]
        return result

    def aggregate(self, pipeline: list) -> Cursor:
        """
        使用提供的管道对MongoDB集合中的文档进行聚合。
        Args:
            pipeline (list): 用于聚合文档的管道。
        Returns:
            Cursor: 匹配管道的文档迭代器。
        """

        cursor = self._collection.aggregate(pipeline)
        return cursor


class AsyncMongoUtils:
    """MongoDB异步操作工具类"""

    def __init__(
        self,
        host: str = None,
        port: Union[int, str] = None,
        username: str = None,
        password: str = None,
        database: str = None,
        collection: str = None,
    ) -> None:
        """
        初始化MongoDB异步工具类，建立数据库连接并配置集合。

        Args:
            host: MongoDB主机地址，默认从环境变量MONGO_HOST获取
            port: MongoDB端口号，默认从环境变量MONGO_PORT获取
            username: MongoDB用户名，默认从环境变量MONGO_USERNAME获取
            password: MongoDB密码，默认从环境变量MONGO_PASSWORD获取
            database: 数据库名称，默认从环境变量MONGO_DATABASE获取
            collection: 集合名称，默认从环境变量MONGO_COLLECTION获取
        """
        self.username = username if username else os.getenv("MONGO_USERNAME", "root")
        self._password = password if password else os.getenv("MONGO_PASSWORD", "root")
        self.host = host if host else os.getenv("MONGO_HOST", "127.0.0.1")
        self.port = int(port) if port else int(os.getenv("MONGO_PORT", 27017))
        self.database_name = database if database else os.getenv("MONGO_DATABASE")
        self.collection_name = (
            collection if collection else os.getenv("MONGO_COLLECTION")
        )

        # 创建连接URI
        if self.username and self._password:
            uri = f"mongodb://{self.username}:{self._password}@{self.host}:{self.port}"
        else:
            uri = f"mongodb://{self.host}:{self.port}"

        # 创建异步客户端
        self._client = AsyncIOMotorClient(uri)
        self._database = self._client[self.database_name]
        self._collection = self._database[self.collection_name]

    async def close(self) -> None:
        """关闭数据库连接"""
        self._client.close()

    async def insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步插入单个文档
        Args:
            data: 要插入的文档数据
        Returns:
            包含inserted_id的插入结果
        """
        result = await self._collection.insert_one(data)
        return {
            "acknowledged": result.acknowledged,
            "inserted_id": str(result.inserted_id),
        }

    async def update(
        self, query: Dict[str, Any], data: Dict[str, Any], upsert: bool = True
    ) -> Dict[str, Any]:
        """
        异步更新文档
        Args:
            query: 查询条件
            data: 更新数据
            upsert: 是否在文档不存在时插入新文档
        Returns:
            更新操作结果
        """
        update_data = {"$set": data}
        result = await self._collection.update_one(
            filter=query, update=update_data, upsert=upsert
        )
        return {
            "acknowledged": result.acknowledged,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None,
        }

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        异步查询单个文档
        Args:
            query: 查询条件
        Returns:
            查询结果文档或None
        """
        # 处理_id字段
        if "_id" in query and isinstance(query["_id"], str):
            try:
                query["_id"] = ObjectId(query["_id"])
            except:
                return None

        result = await self._collection.find_one(query)

        # 处理查询结果
        if result:
            result["_id"] = str(result["_id"])

        return result

    async def find(
        self, query: Dict[str, Any], limit: int = 100, skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        异步查询多个文档
        Args:
            query: 查询条件
            limit: 返回文档最大数量
            skip: 跳过的文档数量
        Returns:
            文档列表
        """
        cursor = self._collection.find(query).skip(skip).limit(limit)
        results = []

        async for doc in cursor:
            doc["_id"] = str(doc["_id"])  # 转换ObjectId为字符串
            results.append(doc)

        return results

    async def delete_one(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步删除单个文档
        Args:
            query: 查询条件
        Returns:
            删除操作结果
        """
        result = await self._collection.delete_one(query)
        return {
            "acknowledged": result.acknowledged,
            "deleted_count": result.deleted_count,
        }

    async def delete_many(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步删除多个文档
        Args:
            query: 查询条件
        Returns:
            删除操作结果
        """
        result = await self._collection.delete_many(query)
        return {
            "acknowledged": result.acknowledged,
            "deleted_count": result.deleted_count,
        }

    async def count_documents(self, query: Dict[str, Any]) -> int:
        """
        异步计算文档数量
        Args:
            query: 查询条件
        Returns:
            符合条件的文档数量
        """
        return await self._collection.count_documents(query)

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        异步聚合操作
        Args:
            pipeline: 聚合管道
        Returns:
            聚合结果列表
        """
        results = []
        async for doc in self._collection.aggregate(pipeline):
            if "_id" in doc and isinstance(doc["_id"], ObjectId):
                doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
