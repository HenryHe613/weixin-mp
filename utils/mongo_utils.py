import os
from pymongo import MongoClient, UpdateOne
from pymongo.cursor import Cursor

class MongoUtils:
    UpdateOne = UpdateOne

    def __init__(self, collection_name:str) -> None:
        """
        使用连接详细信息和集合初始化 MongoWrapper。
        Args:
            collection_name (str): 要交互的集合的名称。
        """
        
        username = os.getenv('MONGO_DB_USERNAME')
        password = os.getenv('MONGO_DB_PASSWORD')
        host = os.getenv('MONGO_DB_HOST')
        port = os.getenv('MONGO_DB_PORT')
        database_name = os.getenv('MONGO_DB_NAME')

        self.__client = MongoClient(
            host=host,
            port=int(port),
            username=username,
            password=password
        )
        self.__database = self.__client[database_name]
        self.__collection = self.__database[collection_name]


    def update(self, query:dict, data:dict) -> dict:
        """
        根据提供的查询条件更新MongoDB集合中的文档。
        Args:
            query (dict): 用于匹配要更新的文档的查询条件。
            data (dict): 用于更新匹配文档的数据。
        Returns:
            dict: 更新操作的结果。
        """
        data = {"$set": data}
        result = self.__collection.update_one(filter=query, update=data, upsert=True)
        return result
    
    
    def bulk_write(self, operations: list) -> dict:
        """
        根据提供的查询条件更新MongoDB集合中的文档。
        Args:
            operations (list): 用于更新文档的操作列表。
        Returns:
            dict: 更新操作的结果。
        """
        result = self.__collection.bulk_write(operations)
        return result
    
    
    def find(self, query: dict, batch_size: int = 100) -> Cursor:
        """
        根据提供的查询条件从MongoDB集合中检索文档。
        Args:
            query (dict): 用于匹配要检索的文档的查询条件。
        Returns:
            Cursor: 匹配查询条件的文档迭代器。
        """
        
        cursor = self.__collection.find(query).batch_size(batch_size)
        return cursor
    
    
    def find_one(self, query:dict) -> dict:
        """
        根据提供的查询条件从MongoDB集合中检索第一个符合的文档。
        Args:
            query (dict): 用于匹配要检索的文档的查询条件。
        Returns:
            dict: 匹配查询条件的文档。
        """
        
        result = self.__collection.find_one(query)
        return result

    def aggregate(self, pipeline: list) -> Cursor:
        """
        使用提供的管道对MongoDB集合中的文档进行聚合。
        Args:
            pipeline (list): 用于聚合文档的管道。
        Returns:
            Cursor: 匹配管道的文档迭代器。
        """
        
        cursor = self.__collection.aggregate(pipeline)
        return cursor