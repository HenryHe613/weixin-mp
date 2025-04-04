import aiomysql
from app.core.logger import LOG
from app.core.config import settings


class MySQL:
    _pool = None

    # 数据库表名
    USERS_TABLE = "users"
    GROUPS_TABLE = "groups"
    USER_GROUPS_TABLE = "user_groups"

    # 日志记录器
    logger = LOG().logger

    @classmethod
    async def create_pool(cls):
        if not cls._pool:
            cls._pool = await aiomysql.create_pool(
                host=settings.mysql_host,
                port=int(settings.mysql_port),
                user=settings.mysql_user,
                password=settings.mysql_password,
                db=settings.mysql_database,
                minsize=settings.mysql_pool_minsize,
                maxsize=settings.mysql_pool_maxsize,
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

    # def create_tables(self) -> None:
    #     """
    #     创建数据库表结构，包括users、groups和user_groups三个表
    #     使用事务确保所有表创建成功或全部回滚
    #     """
    #     self._ensure_connection()
    #     try:
    #         # 开始事务
    #         self._db.start_transaction()

    #         # 创建users表
    #         users_sql = f"""
    #             CREATE TABLE IF NOT EXISTS {self.USERS_TABLE} (
    #                 openid VARCHAR(255) PRIMARY KEY,  -- 微信唯一标识
    #                 nickname VARCHAR(255),            -- 用户昵称
    #                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #             );
    #         """
    #         self._cursor.execute(users_sql)

    #         # 创建groups表
    #         groups_sql = f"""
    #             CREATE TABLE IF NOT EXISTS {self.GROUPS_TABLE} (
    #                 group_id INT AUTO_INCREMENT PRIMARY KEY,
    #                 name VARCHAR(255) NOT NULL UNIQUE,  -- 群组名称, UNIQUE 约束
    #                 owner_openid VARCHAR(255) NOT NULL, -- 群主 openid
    #                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #                 FOREIGN KEY (owner_openid) REFERENCES users(openid)
    #             );
    #         """
    #         self._cursor.execute(groups_sql)

    #         # 创建user_groups表
    #         user_groups_sql = f"""
    #             CREATE TABLE IF NOT EXISTS {self.USER_GROUPS_TABLE} (
    #                 openid VARCHAR(255) NOT NULL,     -- 用户 openid
    #                 group_name VARCHAR(255) NOT NULL, -- 关联的群组名称
    #                 joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #                 PRIMARY KEY (openid, group_name), -- 联合主键避免重复加入
    #                 FOREIGN KEY (openid) REFERENCES users(openid),
    #                 FOREIGN KEY (group_name) REFERENCES groups(name)
    #             );
    #         """
    #         self._cursor.execute(user_groups_sql)

    #         # 提交事务
    #         self._db.commit()
    #         self.logger.info("数据库表创建成功")

    #     except mysql.connector.Error as err:
    #         # 发生错误时回滚事务
    #         self._db.rollback()
    #         self.logger.error(f"创建数据库表时出错: {err}")
    #         raise

    @classmethod
    async def create_user(
        cls,
        conn: aiomysql.Connection,
        openid: str,
        nickname: str,
    ) -> bool:
        """
        创建用户 (异步版本)
        Args:
            conn (aiomysql.Connection): aiomysql 数据库连接对象
            openid (str): 用户的openid
            nickname (str): 用户昵称
        Returns:
            bool: 是否成功创建用户
        Raises:
            aiomysql.Error: 数据库操作错误
        """
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"INSERT INTO {cls.USERS_TABLE} (openid, nickname) VALUES (%s, %s);",
                    (openid, nickname),
                )
            return True
        except aiomysql.IntegrityError as err:
            if err.args[0] == 1062:  # 主键重复错误 (aiomysql 使用 err.args[0])
                cls.logger.warning(f"用户 {openid} 已存在")
            else:
                cls.logger.error(f"创建用户时出错: {err}")
            # aiomysql 的连接在 with 块结束时会自动处理事务（通常是回滚），
            # 如果需要显式回滚，可以使用 await conn.rollback()
            return False
        except aiomysql.Error as err:
            cls.logger.error(f"创建用户时出错: {err}")
            return False

    @classmethod
    async def create_group(
        cls,
        conn: aiomysql.Connection,
        openid: str,
        name: str,
    ) -> bool:
        """
        创建群组 (异步版本)
        对应公众号命令 /group create <name>
        Args:
            conn (aiomysql.Connection): aiomysql 数据库连接对象
            openid (str): 群主的openid
            name (str): 群组名称
        Returns:
            bool: 是否成功创建群组
        Raises:
            aiomysql.Error: 数据库操作错误
        """
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"INSERT INTO {cls.GROUPS_TABLE} (name, owner_openid) VALUES (%s, %s);",
                    (name, openid),
                )
            return True
        except aiomysql.IntegrityError as err:
            if err.args[0] == 1452:  # 外键约束错误
                cls.logger.warning(f"用户 {openid} 不存在")
            elif err.args[0] == 1062:  # 主键重复错误
                cls.logger.warning(f"群组 {name} 已存在")
            else:
                cls.logger.error(f"创建群组时出错: {err}")
            return False
        except aiomysql.Error as err:
            cls.logger.error(f"创建群组时出错: {err}")
            return False

    @classmethod
    async def delete_group(
        cls,
        conn: aiomysql.Connection,
        openid: str,
        group_name: str,
    ) -> bool:
        """
        删除群组 (异步版本)
        对应公众号命令 /group delete <name>
        Args:
            conn (aiomysql.Connection): aiomysql 数据库连接对象
            openid (str): 用户的openid
            group_name (str): 群组名称
        Returns:
            bool: 是否成功删除群组
        Raises:
            aiomysql.Error: 数据库操作错误
        """
        try:
            async with conn.cursor() as cursor:
                # 检查用户是否是群主
                await cursor.execute(
                    f"SELECT group_id FROM {cls.GROUPS_TABLE} WHERE name = %s AND owner_openid = %s;",
                    (group_name, openid),
                )
                if not cursor.fetchone():
                    return False
                # 删除用户-群组关系
                await cursor.execute(
                    f"DELETE FROM {cls.USER_GROUPS_TABLE} WHERE group_name = %s;",
                    (group_name,),
                )
                # 然后删除群组
                await cursor.execute(
                    f"DELETE FROM {cls.GROUPS_TABLE} WHERE name = %s;",
                    (group_name,),
                )
            return True
        except aiomysql.Error as err:
            cls.logger.error(f"删除群组时出错: {err}")
            return False

    @classmethod
    async def join_group(
        cls,
        conn: aiomysql.Connection,
        openid: str,
        group_name: str,
    ) -> bool:
        """
        通过群组名称加入群组 (异步版本)
        对应公众号命令 /group join <name>
        Args:
            conn (aiomysql.Connection): aiomysql 数据库连接对象
            openid (str): 用户的openid
            group_name (str): 群组名称
        Returns:
            bool: 是否成功加入群组
        Raises:
            aiomysql.Error: 数据库操作错误
        """
        try:
            async with conn.cursor() as cursor:
                # 加入群组
                await cursor.execute(
                    f"INSERT INTO {cls.USER_GROUPS_TABLE} (openid, group_name) VALUES (%s, %s);",
                    (openid, group_name),
                )
            cls.logger.info(f"用户 {openid} 成功加入群组 {group_name}")
            return True
        except aiomysql.IntegrityError as err:
            if err.args[0] == 1062:  # 主键重复错误
                cls.logger.warning(f"用户 {openid} 已在群组 {group_name} 中")
            elif err.args[0] == 1452:  # 外键约束错误
                cls.logger.warning(f"用户 {openid} 或群组 {group_name} 不存在")
            else:
                cls.logger.error(f"加入群组时出错: {err}")
            return False
        except aiomysql.Error as err:
            cls.logger.error(f"加入群组时出错: {err}")
            return False

    @classmethod
    async def leave_group(
        cls,
        conn: aiomysql.Connection,
        openid: str,
        group_name: str,
    ) -> bool:
        """
        通过群组名称离开群组 (异步版本)
        对应公众号命令 /group leave <name>
        Args:
            conn (aiomysql.Connection): aiomysql 数据库连接对象
            openid (str): 用户的openid
            group_name (str): 群组名称
        Returns:
            bool: 是否成功离开群组
        Raises:
            aiomysql.Error: 数据库操作错误
        """
        try:
            async with conn.cursor() as cursor:
                # 离开群组
                await cursor.execute(
                    f"DELETE FROM {cls.USER_GROUPS_TABLE} WHERE openid = %s AND group_name = %s;",
                    (openid, group_name),
                )
            cls.logger.info(f"用户 {openid} 成功离开群组 {group_name}")
            return True
        except aiomysql.IntegrityError as err:
            if err.args[0] == 1452:  # 外键约束错误
                cls.logger.warning(f"用户 {openid} 或群组 {group_name} 不存在")
            cls.logger.error(f"离开群组时出错: {err}")
            return False
        except aiomysql.Error as err:
            cls.logger.error(f"离开群组时出错: {err}")
            return False

    @classmethod
    async def get_info(
        cls,
        conn: aiomysql.Connection,
        openid: str,
    ) -> dict:
        """
        获取用户信息 (异步版本)
        对应公众号命令 /group list
        Args:
            conn (aiomysql.Connection): aiomysql 数据库连接对象
            openid (str): 用户的openid
        Returns:
            dict: 用户加入群组的信息
        Raises:
            mysql.connector.Error: 数据库操作错误
        """
        result = {"owner": [], "member": []}
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT group_name FROM {cls.USER_GROUPS_TABLE} WHERE openid = %s;",
                    (openid,),
                )
                result["member"] = [row[0] for row in await cursor.fetchall()]
                await cursor.execute(
                    f"SELECT name FROM {cls.GROUPS_TABLE} WHERE owner_openid = %s;",
                    (openid,),
                )
                result["owner"] = [row[0] for row in await cursor.fetchall()]
        except aiomysql.Error as err:
            cls.logger.error(f"获取用户信息时出错: {err}")
        return result

    @classmethod
    async def get_group_member(
        cls,
        conn: aiomysql.Connection,
        openid: str,
        group_name: str,
    ) -> list:
        """
        获取群组成员 (异步版本)
        Args:
            conn (aiomysql.Connection): aiomysql 数据库连接对象
            openid (str): 用户的openid
            group_name (str): 群组名称
        Returns:
            list: 群组成员列表
        Raises:
            mysql.connector.Error: 数据库操作错误
        """
        result = []
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT * FROM {cls.GROUPS_TABLE} WHERE owner_openid = %s AND name = %s;",
                    (openid, group_name),
                )
                if not await cursor.fetchone():
                    return result
                await cursor.execute(
                    f"SELECT * FROM {cls.USER_GROUPS_TABLE} WHERE group_name = %s;",
                    (group_name,),
                )
                for i in await cursor.fetchall():
                    result.append(i[0])
        except aiomysql.IntegrityError as err:
            if err.args[0] == 1452:  # 外键约束错误
                cls.logger.warning(f"用户 {openid} 或群组 {group_name} 不存在")
            else:
                cls.logger.error(f"获取群组成员时出错: {err}")
        except aiomysql.Error as err:
            cls.logger.error(f"获取群组成员时出错: {err}")
        print(result)
        return result


if __name__ == "__main__":
    pass
