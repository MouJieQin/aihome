"""
This module provides a `LightBedroom` class for controlling bedroom lights and fans
using the Home Assistant Python API. It allows users to perform various operations
such as turning lights on/off, switching light modes, and adjusting fan speed.
"""

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
        self._turn_on(self.light_entity_id, "light")

    def turn_off_light(self) -> None:
        """
        Turns off the bedroom light.
        """
        self._turn_off(self.light_entity_id, "light")

    def switch_light(self, value: bool) -> None:
        """
        Switches the bedroom light on or off based on the provided boolean value.

        Args:
            value (bool): If True, turns on the light; if False, turns off the light.
        """
        self._switch(self.light_entity_id, value, "light")

    def set_light_mode(self, mode: str) -> None:
        """
        Activates the light mode for the bedroom light.

        Args:
            mode (str): The light mode to activate.
        """
        self._call_service(
            "light", "turn_on", {"entity_id": self.light_entity_id, "effect": mode}
        )

    def adjust_light_brightness_color_temp(
        self, brightness: int, color_temp_kelvin: int
    ) -> None:
        """
        Adjusts the brightness and color temperature of the bedroom light.
        Args:
            brightness (int): The desired brightness value (0-255).
            color_temp_kelvin (int): The desired color temperature in Kelvin (3000-5700).
        """
        self._call_service(
            "light",
            "turn_on",
            {
                "entity_id": self.light_entity_id,
                "brightness": brightness,
                "color_temp_kelvin": color_temp_kelvin,
            },
        )

    def turn_on_fan(self) -> None:
        """
        Turns on the bedroom fan.
        """
        self._turn_on(self.fan_entity_id, "fan")

    def turn_off_fan(self) -> None:
        """
        Turns off the bedroom fan.
        """
        self._turn_off(self.fan_entity_id, "fan")

    def switch_fan(self, value: bool) -> None:
        """
        Switches the bedroom fan on or off based on the provided boolean value.

        Args:
            value (bool): If True, turns on the fan; if False, turns off the fan.
        """
        self._switch(self.fan_entity_id, value, "fan")

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
            index (int): The index of the preset speed value for the fan.
        """
        preset_values = [1, 22, 46, 70, 86, 100]
        if 0 <= value < len(preset_values):
            self.adjust_fan_speed(preset_values[value])
        else:
            logger.error(f"Index {value} out of range for preset values")

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

    def get_light_state(self) -> Dict:
        """
        Retrieves the state of the bedroom light.
        Returns:
            Dict: The state of the bedroom light.
        """
        state_details = self._get_entity_state(self.light_entity_id)
        return {
            "state": state_details.get("state"),
            "brightness": state_details.get("attributes", {}).get("brightness"),
            "color_temp_kelvin": state_details.get("attributes", {}).get(
                "color_temp_kelvin"
            ),
            "effect": state_details.get("attributes", {}).get("effect"),
            "rgb_color": state_details.get("attributes", {}).get("rgb_color"),
            # "min_color_temp_kelvin": state_details.get("attributes", {}).get(
            #     "min_color_temp_kelvin"
            # ),
            # "max_color_temp_kelvin": state_details.get("attributes", {}).get(
            #     "max_color_temp_kelvin"
            # ),
            # "effect_list": state_details.get("attributes", {}).get("effect_list"),
        }

    def get_fan_state(self) -> Dict:
        """
        Retrieves the state of the bedroom fan.
        Returns:
            Dict: The state of the bedroom fan.
        """
        state_details = self._get_entity_state(self.fan_entity_id)
        return {
            "state": state_details.get("state"),
        }

    def get_fan_speed_state(self) -> Dict:
        """
        Retrieves the state of the bedroom fan speed.
        Returns:
            Dict: The state of the bedroom fan speed.
        """
        state_details = self._get_entity_state(self.fan_speed_entity_id)
        return {
            "state": state_details.get("state"),
        }

    def get_states(self) -> Dict:
        """
        Retrieves the states of the bedroom light and fan.
        Returns:
            Dict: A dictionary containing the states of the bedroom light and fan.
        """
        return {
            "light": self.get_light_state(),
            "fan": self.get_fan_state(),
            "fan_speed": self.get_fan_speed_state(),
        }
