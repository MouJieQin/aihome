"""
This module provides a `LightBedroom` class for controlling bedroom lights and fans
using the Home Assistant Python API. It allows users to perform various operations
such as turning lights on/off, switching light modes, and adjusting fan speed.
"""

from homeassistant_api import Client
from typing import Dict, Any
from libs.log_config import logger
from libs.home_assistant_base import HomeAssistantDevice


class LightBedroom(HomeAssistantDevice):
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
        super().__init__(config, "light_bedroom")
        self.light_entity_id = self.entity_ids["light"]
        self.fan_entity_id = self.entity_ids["fan"]
        self.fan_speed_entity_id = self.entity_ids["fan_speed"]

    def turn_on_light(self) -> None:
        """
        Turns on the bedroom light.
        """
        self._turn_on(self.light_entity_id)

    def turn_off_light(self) -> None:
        """
        Turns off the bedroom light.
        """
        self._turn_off(self.light_entity_id)

    def switch_light(self, value: bool) -> None:
        """
        Switches the bedroom light on or off based on the provided boolean value.

        Args:
            value (bool): If True, turns on the light; if False, turns off the light.
        """
        self._switch(self.light_entity_id, value)

    def set_light_mode(self, mode: str) -> None:
        """
        Activates the light mode for the bedroom light.

        Args:
            mode (str): The light mode to activate.
        """
        self._call_service(
            "light", "turn_on", {"entity_id": self.light_entity_id, "effect": mode}
        )

    def turn_on_fan(self) -> None:
        """
        Turns on the bedroom fan.
        """
        self._turn_on(self.fan_entity_id)

    def turn_off_fan(self) -> None:
        """
        Turns off the bedroom fan.
        """
        self._turn_off(self.fan_entity_id)

    def switch_fan(self, value: bool) -> None:
        """
        Switches the bedroom fan on or off based on the provided boolean value.

        Args:
            value (bool): If True, turns on the fan; if False, turns off the fan.
        """
        self._switch(self.fan_entity_id, value)

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

    def adjust_fan_speed_to_preset_value(self, index: int) -> None:
        """
        Adjusts the speed of the bedroom fan to a preset value.

        Args:
            index (int): The index of the preset speed value for the fan.
        """
        preset_values = [1, 22, 46, 70, 86, 100]
        if 0 <= index < len(preset_values):
            self.adjust_fan_speed(preset_values[index])
        else:
            logger.error(f"Index {index} out of range for preset values")

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
        Sets the bedroom fan speed to the fourth preset value (70).
        """
        self.adjust_fan_speed(70)
