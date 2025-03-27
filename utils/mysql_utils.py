import os
import mysql.connector
from typing import Union
from utils.log_utils import LOG


class MysqlUtils:
    # 日志记录器
    logger = LOG().logger

    # 数据库表名
    USERS_TABLE = "users"
    GROUPS_TABLE = "groups"
    USER_GROUPS_TABLE = "user_groups"

    def __init__(
        self,
        host: str = None,
        user: str = None,
        password: str = None,
        database: str = None,
        port: Union[int, str] = None,
    ) -> None:
        """
        初始化MySQL连接工具类

        Args:
            host (str, optional): MySQL主机地址，默认从环境变量MYSQL_HOST获取，若无则为127.0.0.1
            user (str, optional): MySQL用户名，默认从环境变量MYSQL_USER获取，若无则为root
            password (str, optional): MySQL密码，默认从环境变量MYSQL_PASSWORD获取，若无>则为root
            database (str, optional): 数据库名称，默认从环境变量MYSQL_DATABASE获取，若无则为test
            port (Union[int, str], optional): MySQL端口，默认从环境变量MYSQL_PORT获取，若无则为3306
        """
        self.host = host if host else os.getenv("MYSQL_HOST", "127.0.0.1")
        self.port = int(port) if port else int(os.getenv("MYSQL_PORT", 3306))
        self.user = user if user else os.getenv("MYSQL_USER", "root")
        self._password = password if password else os.getenv("MYSQL_PASSWORD", "root")
        self.database = database if database else os.getenv("MYSQL_DATABASE", "weixin")

        self._db = mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self._password,
            database=self.database,
        )
        self._cursor = self._db.cursor()
        self.logger.debug(f"MySQL已连接")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if hasattr(self, "_cursor") and self._cursor:
            self._cursor.close()
        if hasattr(self, "_db") and self._db:
            self._db.close()
        self.logger.debug("MySQL连接已关闭")

    def _ensure_connection(self):
        try:
            self._db.ping(reconnect=True, attempts=3, delay=5)
        except mysql.connector.Error as err:
            self.logger.error(f"数据库连接检查失败: {err}")
            raise

    def create_tables(self) -> None:
        """
        创建数据库表结构，包括users、groups和user_groups三个表

        使用事务确保所有表创建成功或全部回滚
        """
        self._ensure_connection()
        try:
            # 开始事务
            self._db.start_transaction()

            # 创建users表
            users_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.USERS_TABLE} (
                    openid VARCHAR(255) PRIMARY KEY,  -- 微信唯一标识
                    nickname VARCHAR(255),            -- 用户昵称
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            self._cursor.execute(users_sql)

            # 创建groups表
            groups_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.GROUPS_TABLE} (
                    group_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,  -- 群组名称, UNIQUE 约束
                    owner_openid VARCHAR(255) NOT NULL, -- 群主 openid
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_openid) REFERENCES users(openid)
                );
            """
            self._cursor.execute(groups_sql)

            # 创建user_groups表
            user_groups_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.USER_GROUPS_TABLE} (
                    openid VARCHAR(255) NOT NULL,     -- 用户 openid
                    group_name VARCHAR(255) NOT NULL, -- 关联的群组名称
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (openid, group_name), -- 联合主键避免重复加入
                    FOREIGN KEY (openid) REFERENCES users(openid),
                    FOREIGN KEY (group_name) REFERENCES groups(name)
                );
            """
            self._cursor.execute(user_groups_sql)

            # 提交事务
            self._db.commit()
            self.logger.info("数据库表创建成功")

        except mysql.connector.Error as err:
            # 发生错误时回滚事务
            self._db.rollback()
            self.logger.error(f"创建数据库表时出错: {err}")
            raise

    def create_user(self, openid: str, nickname: str) -> bool:
        """
        创建用户

        Args:
            openid (str): 用户的openid
            nickname (str): 用户昵称

        Returns:
            bool: 是否成功创建用户

        Raises:
            mysql.connector.Error: 数据库操作错误
        """
        self._ensure_connection()
        try:
            sql = f"""
                INSERT INTO {self.USERS_TABLE} (openid, nickname)
                VALUES (%s, %s);
            """
            self._cursor.execute(sql, (openid, nickname))
            self._db.commit()
            return True
        except mysql.connector.errors.IntegrityError as err:
            if err.errno == 1062:  # 主键重复错误
                self.logger.warning(f"用户 {openid} 已存在")
            else:
                self.logger.error(f"创建用户时出错: {err}")
            self._db.rollback()
            return False
        except mysql.connector.Error as err:
            self._db.rollback()
            self.logger.error(f"创建用户时出错: {err}")
            return False

    def create_group(self, openid: str, name: str) -> bool:
        """
        创建群组
        对应公众号命令 /group create <name>

        Args:
            openid (str): 群主的openid
            name (str): 群组名称

        Returns:
            bool: 是否成功创建群组

        Raises:
            MysqlUtils.NoSuchUserError: 未找到对应的用户
            mysql.connector.Error: 数据库操作错误
        """
        self._ensure_connection()
        try:
            sql = f"""
                INSERT INTO {self.GROUPS_TABLE} (name, owner_openid)
                VALUES (%s, %s);
            """
            self._cursor.execute(sql, (name, openid))
            self._db.commit()
            return True
        except mysql.connector.errors.IntegrityError as err:
            if err.errno == 1452:  # 外键约束错误
                self.logger.warning(f"用户 {openid} 不存在")
            elif err.errno == 1062:  # 主键重复错误
                self.logger.warning(f"群组 {name} 已存在")
            else:
                self.logger.error(f"创建群组时出错: {err}")
            self._db.rollback()
            return False
        except mysql.connector.Error as err:
            self._db.rollback()
            self.logger.error(f"创建群组时出错: {err}")
            return False

    def delete_group(self, openid: str, group_name: str) -> bool:
        """
        删除群组
        对应公众号命令 /group delete <name>

        Args:
            openid (str): 用户的openid
            group_name (str): 群组名称

        Returns:
            bool: 是否成功删除群组

        Raises:
            mysql.connector.Error: 数据库操作错误
        """
        self._ensure_connection()
        try:
            # 检查用户是否是群主
            check_sql = f"""
                SELECT group_id FROM {self.GROUPS_TABLE}
                WHERE name = %s AND owner_openid = %s;
            """
            self._cursor.execute(check_sql, (group_name, openid))
            if not self._cursor.fetchone():
                return False
            # 删除用户-群组关系
            delete_user_groups_sql = f"""
                DELETE FROM {self.USER_GROUPS_TABLE}
                WHERE group_name = %s;
            """
            self._cursor.execute(delete_user_groups_sql, (group_name,))
            # 然后删除群组
            delete_group_sql = f"""
                DELETE FROM {self.GROUPS_TABLE}
                WHERE name = %s;
            """
            self._cursor.execute(delete_group_sql, (group_name,))
            self._db.commit()
            return True
        except mysql.connector.Error as err:
            self._db.rollback()
            self.logger.error(f"删除群组时出错: {err}")
            return False

    def join_group(self, openid: str, group_name: str) -> bool:
        """
        通过群组名称加入群组
        对应公众号命令 /group join <name>

        Args:
            openid (str): 用户的openid
            group_name (str): 群组名称

        Returns:
            bool: 是否成功加入群组

        Raises:
            mysql.connector.Error: 数据库操作错误
        """
        self._ensure_connection()
        try:
            # 加入群组
            join_sql = f"""
                INSERT INTO {self.USER_GROUPS_TABLE} (openid, group_name)
                VALUES (%s, %s);
            """
            self._cursor.execute(join_sql, (openid, group_name))
            self._db.commit()
            self.logger.info(f"用户 {openid} 成功加入群组 {group_name}")
            return True
        except mysql.connector.errors.IntegrityError as err:
            self._db.rollback()
            if err.errno == 1062:  # 主键重复错误
                self.logger.warning(f"用户 {openid} 已在群组 {group_name} 中")
            elif err.errno == 1452:  # 外键约束错误
                self.logger.warning(f"用户 {openid} 或群组 {group_name} 不存在")
            else:
                self.logger.error(f"加入群组时出错: {err}")
            return False
        except mysql.connector.Error as err:
            self._db.rollback()
            self.logger.error(f"加入群组时出错: {err}")
            return False

    def leave_group(self, openid: str, group_name: str) -> bool:
        """
        通过群组名称离开群组
        对应公众号命令 /group leave <name>

        Args:
            openid (str): 用户的openid
            group_name (str): 群组名称

        Returns:
            bool: 是否成功离开群组

        Raises:
            mysql.connector.Error: 数据库操作错误
        """
        self._ensure_connection()
        try:
            # 离开群组
            leave_sql = f"""
                DELETE FROM {self.USER_GROUPS_TABLE}
                WHERE openid = %s AND group_name = %s;
            """
            self._cursor.execute(leave_sql, (openid, group_name))
            self._db.commit()
            self.logger.info(f"用户 {openid} 成功离开群组 {group_name}")
            return True
        except mysql.connector.errors.IntegrityError as err:
            self._db.rollback()
            if err.errno == 1452:  # 外键约束错误
                self.logger.warning(f"用户 {openid} 或群组 {group_name} 不存在")
            self.logger.error(f"离开群组时出错: {err}")
            return False
        except mysql.connector.Error as err:
            self._db.rollback()
            self.logger.error(f"离开群组时出错: {err}")
            return False

    def get_info(self, openid: str) -> dict:
        """
        获取用户信息
        对应公众号命令 /group list
        """
        self._ensure_connection()
        result = {"owner": [], "member": []}
        try:
            member_sql = f"""
                SELECT group_name FROM {self.USER_GROUPS_TABLE} WHERE openid = %s;
            """
            self._cursor.execute(member_sql, (openid,))
            result["member"] = [row[0] for row in self._cursor.fetchall()]
            owner_sql = f"SELECT name FROM {self.GROUPS_TABLE} WHERE owner_openid = %s;"
            self._cursor.execute(owner_sql, (openid,))
            result["owner"] = [row[0] for row in self._cursor.fetchall()]
        except mysql.connector.Error as err:
            self.logger.error(f"获取用户信息时出错: {err}")
        return result

    def get_group_member(self, openid: str, group_name: str) -> list:
        """
        获取群组成员
        """
        self._ensure_connection()
        try:
            result = []
            sql = f"""
                SELECT * FROM {self.GROUPS_TABLE} WHERE owner_openid = %s AND name = %s;
            """
            self._cursor.execute(sql, (openid, group_name))
            if not self._cursor.fetchone():
                return result
            sql = f"""
                SELECT * FROM {self.USER_GROUPS_TABLE} WHERE group_name = %s;
            """
            self._cursor.execute(sql, (group_name,))
            for i in self._cursor.fetchall():
                result.append(i[0])
        except mysql.connector.errors.IntegrityError as err:
            if err.errno == 1452:  # 外键约束错误
                self.logger.warning(f"用户 {openid} 或群组 {group_name} 不存在")
            else:
                self.logger.error(f"获取群组成员时出错: {err}")
            return result
        except mysql.connector.Error as err:
            self.logger.error(f"获取群组成员时出错: {err}")
            return result


if __name__ == "__main__":
    pass
