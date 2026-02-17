import os
import logging
from logging.handlers import RotatingFileHandler
from .config_loader import get_config

# 默认日志目录
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "logs",
)
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


class Logger:
    """
    集中式日志系统
    - 同时输出到控制台 (Console) 和文件 (File)
    - 文件按大小自动分割 (Rotating)
    - 可通过 config.ini 配置开关
    """

    _instance = None
    logger = None

    def __new__(cls, name="BinanceQuant"):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize(name)
        return cls._instance

    def _initialize(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Avoid adding handlers multiple times
        if self.logger.handlers:
            return

        # 读取配置开关
        # 用户要求: 不使用 try-except 包裹配置读取
        enable_logging = get_config("enable_logging", section="system")

        # 仅支持 true (不区分大小写)
        if str(enable_logging).lower() != "true":
            self.logger.addHandler(logging.NullHandler())
            return

        # 格式化
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 1. 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 2. 文件处理器 (按日期命名，每天一个新文件，或者按大小分割)
        # 这里使用 RotatingFileHandler，每个文件最大 10MB，保留 5 个备份
        log_file = os.path.join(LOG_DIR, "system.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger


# 全局单例
system_logger = Logger().get_logger()


def get_logger(module_name=None):
    """
    获取带模块名的子日志记录器
    用法: logger = get_logger(__name__)
    """
    if module_name:
        return system_logger.getChild(module_name)
    return system_logger
