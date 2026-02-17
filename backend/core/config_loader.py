import configparser
import os


def get_config(*keys: str, section: str):
    """
    从 config.ini 获取配置
    :param keys: 配置项名称
    :param section: 配置段落 (必须指定)
    :return: 单个值或值的元组
    """
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")

    if not config.read(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if not config.has_section(section):
        raise ValueError(f"Section '{section}' not found in config.ini")

    values = []
    for key in keys:
        if config.has_option(section, key):
            values.append(config.get(section, key))
        else:
            values.append(None)

    return values[0] if len(values) == 1 else values
