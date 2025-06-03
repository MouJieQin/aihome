from homeassistant_api import Client
from typing import Dict, Any
from libs.log_config import logger


class HomeAssistantDevice:
    """
    Home Assistant设备基类，提供基本的服务调用和状态获取功能
    """

    def __init__(self, config: Dict[str, Any], device_config_key: str):
        """
        初始化Home Assistant设备基类

        Args:
            config (Dict[str, Any]): 配置字典
            device_config_key (str): 设备配置在smart_home_appliances中的键名
        """
        ha_config = config["home_assistant"]
        device_config = config["smart_home_appliances"][device_config_key]
        api_url = f"http://{ha_config['host']}:{ha_config['port']}/api"
        self.client = Client(api_url, ha_config["long_lived_access_token"])
        self.entity_ids = device_config["entity_id"]

    def _call_service(self, domain: str, service: str, data: Dict[str, Any]) -> None:
        """
        调用Home Assistant服务

        Args:
            domain (str): 服务域
            service (str): 服务名称
            data (Dict[str, Any]): 服务数据
        """
        try:
            res = self.client.trigger_service(domain, service, **data)
            logger.info(res)
        except Exception as e:
            logger.exception(e)

    def get_entity_state(self, entity_id: str) -> Dict:
        """
        获取实体状态

        Args:
            entity_id (str): 实体ID

        Returns:
            Dict: 实体状态
        """
        try:
            state = self.client.get_state(entity_id)
            return state
        except Exception as e:
            logger.exception(e)
            return {}
