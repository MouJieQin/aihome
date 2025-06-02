"""
This module provides a `LightBedroom` class for controlling bedroom lights and fans
using the Home Assistant Python API. It allows users to perform various operations
such as turning lights on/off, switching light modes, and adjusting fan speed.
"""

from homeassistant_api import Client
from typing import Dict, Any
from libs.log_config import logger


class LightBedroom:
    """
    A class for controlling bedroom lights and fans using the Home Assistant Python API.

    Attributes:
        client (Client): Home Assistant API client instance.
        light_entity_id (str): Entity ID for the bedroom light.
        fan_entity_id (str): Entity ID for the bedroom fan.
        fan_speed_entity_id (str): Entity ID for the bedroom fan speed control.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the bedroom light and fan controller using the Home Assistant Python API.

        Args:
            config (Dict[str, Any]): Configuration dictionary containing Home Assistant
                and device entity information. The expected structure is:
                {
                    "home_assistant": {
                        "host": str,
                        "port": int,
                        "long_lived_access_token": str
                    },
                    "smart_home_appliances": {
                        "light_bedroom": {
                            "entity_id": {
                                "light": str,
                                "fan": str,
                                "fan_speed": str
                            }
                        }
                    }
                }
        """
        ha_config = config["home_assistant"]
        light_config = config["smart_home_appliances"]["light_bedroom"]
        api_url = f"http://{ha_config['host']}:{ha_config['port']}/api"
        self.client = Client(api_url, ha_config["long_lived_access_token"])
        self.light_entity_id = light_config["entity_id"]["light"]
        self.fan_entity_id = light_config["entity_id"]["fan"]
        self.fan_speed_entity_id = light_config["entity_id"]["fan_speed"]

    def _call_service(self, domain: str, service: str, data: Dict[str, Any]) -> None:
        """
        Calls a Home Assistant service.

        Args:
            domain (str): The domain of the service (e.g., 'light', 'fan').
            service (str): The name of the service (e.g., 'turn_on', 'turn_off').
            data (Dict[str, Any]): The data to pass to the service.
        """
        try:
            res = self.client.trigger_service(domain, service, **data)
            logger.info(res)
        except Exception as e:
            logger.exception(e)

    def turn_on_light(self) -> None:
        """
        Turns on the bedroom light by calling the Home Assistant `light.turn_on` service.
        """
        self._call_service("light", "turn_on", {"entity_id": self.light_entity_id})

    def turn_off_light(self) -> None:
        """
        Turns off the bedroom light by calling the Home Assistant `light.turn_off` service.
        """
        self._call_service("light", "turn_off", {"entity_id": self.light_entity_id})

    def switch_light(self, value: bool) -> None:
        """
        Switches the bedroom light on or off based on the provided boolean value.
        Args:
            value (bool): If True, turns on the light; if False, turns off the light.
        """
        if value:
            self.turn_on_light()
        else:
            self.turn_off_light()

    def set_light_mode(self, mode: str) -> None:
        """
        Activates the light mode for the bedroom light.
        """
        self._call_service(
            "light", "turn_on", {"entity_id": self.light_entity_id, "effect": mode}
        )

    def turn_on_light_mode_night(self) -> None:
        """
        Activates the night light mode for the bedroom light.
        """
        self.set_light_mode("Night Light")

    def turn_on_light_mode_movie(self) -> None:
        """
        Activates the movie mode for the bedroom light.
        """
        self.set_light_mode("Cinema Mode")

    def turn_on_light_mode_entertainment(self) -> None:
        """
        Activates the entertainment mode for the bedroom light.
        """
        self.set_light_mode("Entertainment Mode")

    def turn_on_light_mode_reception(self) -> None:
        """
        Activates the reception mode for the bedroom light.
        """
        self.set_light_mode("Reception Mode")

    def turn_off_fan(self) -> None:
        """
        Turns off the bedroom fan by calling the Home Assistant `fan.turn_off` service.
        """
        self._call_service("fan", "turn_off", {"entity_id": self.fan_entity_id})

    def turn_on_fan(self) -> None:
        """
        Turns on the bedroom fan by calling the Home Assistant `fan.turn_on` service.
        """
        self._call_service("fan", "turn_on", {"entity_id": self.fan_entity_id})

    def switch_fan(self, value: bool) -> None:
        """
        Switches the bedroom fan on or off based on the provided boolean value.
        Args:
            value (bool): If True, turns on the fan; if False, turns off the fan.
        """
        if value:
            self.turn_on_fan()
        else:
            self.turn_off_fan()

    def adjust_fan_speed(self, value: int) -> None:
        """
        Adjusts the speed of the bedroom fan.

        Args:
            value (int): The desired speed value for the fan.
        """
        self._call_service(
            "number",
            "set_value",
            {"entity_id": self.fan_speed_entity_id, "value": value},
        )

    def adjust_fan_speed_to_preset_value(self, value: int) -> None:
        """
        Adjusts the speed of the bedroom fan to a preset value.
        Args:
            value (int): The preset speed value for the fan.
        """
        preset_values = [1, 22, 46, 70, 86, 100]
        self.adjust_fan_speed(preset_values[value])

    def adjust_fan_speed_to_max(self) -> None:
        """
        Sets the bedroom fan speed to the maximum value (100).
        """
        self.adjust_fan_speed(100)

    def adjust_fan_speed_to_min(self) -> None:
        """
        Sets the bedroom fan speed to the minimum value (1).
        """
        self.adjust_fan_speed(1)

    def adjust_fan_speed_to_fourth(self) -> None:
        """
        Sets the bedroom fan speed to the fourth preset value (69).
        """
        self.adjust_fan_speed(69)
