import os
import logging
from app.core.config import settings


class LOG:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    # 日志级别映射字典
    LOG_LEVEL_MAP = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    def __init__(self, name: str = None, level: int = None):
        """
        初始化日志器

        Args:
            name (str, optional): 日志器名称，默认为当前文件名
            level (int, optional): 日志级别，如果为None则从环境变量获取
        """

        class ColoredFormatter(logging.Formatter):
            """自定义的格式化器，为不同级别的日志设置不同的颜色"""

            FORMATS = {  # 定义不同级别对应的格式
                logging.DEBUG: "[%(asctime)s]\033[36m[%(levelname)s]\033[92m[%(funcName)s]\033[0m %(message)s",
                logging.INFO: "[%(asctime)s]\033[94m[%(levelname)s]\033[92m[%(funcName)s]\033[0m %(message)s",
                logging.WARNING: "[%(asctime)s]\033[33m[%(levelname)s]\033[92m[%(funcName)s]\033[0m %(message)s",
                logging.ERROR: "[%(asctime)s]\033[31m[%(levelname)s]\033[92m[%(funcName)s]\033[0m %(message)s",
                logging.CRITICAL: "\033[45m\033[93m[%(asctime)s][%(levelname)s][%(funcName)s]\033[0m %(message)s",
            }

            def format(self, record):  # 获取对应级别的格式，如果没有则使用 DEBUG 的格式
                log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.DEBUG])
                formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
                return formatter.format(record)

        # 如果没有提供name参数，使用当前文件名(不含扩展名)
        if name is None:
            import inspect

            # 获取调用者的文件名
            caller_frame = inspect.stack()[1]
            caller_file = caller_frame.filename
            name = os.path.splitext(os.path.basename(caller_file))[0]

        # 从环境变量获取日志级别，如果没有，则使用参数或默认值
        env_level = settings.log_level.upper()
        if level is None:
            level = self.LOG_LEVEL_MAP.get(env_level, logging.DEBUG)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 禁用日志传播
        self.logger.propagate = False

        # 避免重复添加handler
        if not self.logger.handlers:
            # 创建控制台处理器 (带颜色)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(ColoredFormatter())

            # 添加处理器
            self.logger.addHandler(console_handler)
