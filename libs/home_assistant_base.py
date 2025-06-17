from homeassistant_api import Client
from typing import Dict, Optional, Any, Callable
from libs.log_config import logger
from libs.homeassistant_vm_manager import VirtualBoxController
from libs.speaker import Speaker
import time


class HomeAssistantDevice:
    """
    Base class for Home Assistant devices, providing basic service call and state retrieval functions.
    """

    def __init__(self, config: Dict[str, Any], device_config_key: str):
        """
        Initializes the Home Assistant device base class.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
            device_config_key (str): The key name of the device configuration in 'smart_home_appliances'.
        """
        ha_config = config["home_assistant"]
        device_config = config["smart_home_appliances"][device_config_key]
        api_url = f"http://{ha_config['host']}:{ha_config['port']}/api"
        self.client = Client(api_url, ha_config["long_lived_access_token"])
        self.entity_ids = device_config["entity_id"]
        self.ha_vm_manager = VirtualBoxController(config["virtualbox"]["ha_vm_uuid"])
        self.speaker = Speaker(config)

    def _call_service(self, domain: str, service: str, data: Dict[str, Any]) -> None:
        """
        Calls a Home Assistant service.

        Args:
            domain (str): The domain of the service (e.g., 'climate', 'switch').
            service (str): The name of the service (e.g., 'turn_on', 'set_temperature').
            data (Dict[str, Any]): The data to pass to the service.
        """
        try:
            logger.info(f"Calling service {domain}.{service} with data: {data}")
            res = self.client.trigger_service(domain, service, **data)
            logger.info(res)
        except Exception as e:
            if not self.ha_vm_manager.is_vm_running():
                self.speaker.speak_text("Home Assistant未运行，正在尝试启动。")
                if self.ha_vm_manager.start_ha_vm_until_ready():
                    self._call_service(domain, service, data)
                else:
                    self.speaker.speak_text("Home Assistant启动失败，请检查配置")
                    logger.error("Home Assistant启动失败，请检查配置")
            else:
                logger.error(f"Failed to call service {domain}.{service}: {e}")
                self.speaker.speak_text(f"调用服务失败: {domain}.{service}")

    def _turn_on(self, entity_id: str, domain: str = "switch") -> None:
        """Turns on the device."""
        self._call_service(domain, "turn_on", {"entity_id": entity_id})

    def _turn_off(self, entity_id: str, domain: str = "switch") -> None:
        """Turns off the device."""
        self._call_service(domain, "turn_off", {"entity_id": entity_id})

    def _switch(self, entity_id: str, value: bool, domain: str = "switch") -> None:
        """
        Switches the device state.

        Args:
            entity_id (str): The ID of the entity.
            value (bool): True to turn on, False to turn off.
        """
        if value:
            self._turn_on(entity_id, domain)
        else:
            self._turn_off(entity_id, domain)

    def _toggle(self, entity_id: str) -> None:
        """Toggles the device state."""
        self._call_service("switch", "toggle", {"entity_id": entity_id})

    def _get_state(self, entity_id: str) -> bool:
        """Retrieves the device state.

        Returns:
            bool: True if the device is on, False otherwise.
        """
        state = self._get_entity_state(entity_id)
        return state.get("state") == "on"

    def _get_entity_state(self, entity_id: str) -> Dict:
        """
        Retrieves the entity state.

        Args:
            entity_id (str): The ID of the entity.

        Returns:
            Dict: The entity state.
        """
        try:
            state = self.client.get_state(entity_id=entity_id)
            if state:
                return dict(state)
            else:
                logger.error(f"Entity {entity_id} not found.")
                return None  # type: ignore
        except Exception as e:
            logger.error(f"Failed to get the state of {entity_id}: {e}")
            if not self.ha_vm_manager.is_vm_running():
                self.speaker.speak_text("Home Assistant未运行，正在尝试启动。")
                if self.ha_vm_manager.start_ha_vm_until_ready():
                    return self._get_entity_state(entity_id)
                else:
                    self.speaker.speak_text("Home Assistant启动失败，请检查配置")
                    logger.error("Home Assistant启动失败，请检查配置")
                    return None  # type: ignore
            return None  # type: ignore
