from typing import Union, Dict, Any, List, Optional
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from app.core.config import settings


# class MongoDB:
#     """MongoDB异步操作工具类"""

#     def __init__(
#         self,
#         host: str = None,
#         port: Union[int, str] = None,
#         username: str = None,
#         password: str = None,
#         database: str = None,
#         collection: str = None,
#     ) -> None:
#         """
#         初始化MongoDB异步工具类，建立数据库连接并配置集合。
#         Args:
#             host: MongoDB主机地址，默认从环境变量MONGO_HOST获取
#             port: MongoDB端口号，默认从环境变量MONGO_PORT获取
#             username: MongoDB用户名，默认从环境变量MONGO_USERNAME获取
#             password: MongoDB密码，默认从环境变量MONGO_PASSWORD获取
#             database: 数据库名称，默认从环境变量MONGO_DATABASE获取
#             collection: 集合名称，默认从环境变量MONGO_COLLECTION获取
#         """
#         self.host = host if host else settings.mongo_host
#         self.port = int(port) if port else int(settings.mongo_port)
#         self.username = username if username else settings.mongo_username
#         self._password = password if password else settings.mongo_password
#         self.database_name = database if database else settings.mongo_database
#         self.collection_name = collection if collection else settings.mongo_collection

#         # 创建异步客户端
#         self._client = AsyncIOMotorClient(
#             host=self.host,
#             port=self.port,
#             username=self.username,
#             password=self._password,
#         )
#         self._database = self._client[self.database_name]
#         self._collection = self._database[self.collection_name]


class MongoDB:
    """MongoDB异步操作工具类 (FastAPI适配版)"""

    def __init__(
        self,
        client: AsyncIOMotorClient,
        database: str = None,
        collection: str = None,
    ) -> None:
        """
        初始化MongoDB工具类,使用外部传入的客户端实例
        Args:
            client: 已连接的AsyncIOMotorClient实例
            database: 数据库名称（默认使用配置）
            collection: 集合名称（默认使用配置）
        """
        self.database_name = database or settings.mongo_database
        self.collection_name = collection or settings.mongo_collection

        self._client = client
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
        self,
        query: Dict[str, Any],
        data: Dict[str, Any],
        upsert: bool = True,
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
        self,
        query: Dict[str, Any],
        limit: int = 100,
        skip: int = 0,
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
