from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API 配置
    domain: str
    main_path: str = "/wechat"
    web_port: int = 80

    # 微信配置
    appid: str
    appsecret: str
    verify_token: str
    template_id: str

    # MySQL 配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str
    mysql_database: str

    # MySQL 线程池配置
    mysql_pool_minsize: int = 1
    mysql_pool_maxsize: int = 10

    # MongoDB 配置
    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_username: str
    mongo_password: str
    mongo_database: str
    mongo_collection: str

    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # 日志配置
    log_level: str = "INFO"

    # 使用新的配置模式替换旧版 Config 类
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,  # 允许小写环境变量
    )

    @field_validator("log_level")
    def validate_log_level(cls, v):
        if v not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            raise ValueError("Invalid log level")
        return v


# 单例配置对象
settings = Settings()
