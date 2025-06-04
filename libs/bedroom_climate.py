"""
This module provides a `ClimateBedroom` class for controlling bedroom climate devices
using the Home Assistant Python API. It allows users to perform various operations
such as turning the climate device on/off, switching modes, and setting temperature.
"""

from homeassistant_api import Client
from typing import Dict, Any
from libs.log_config import logger
from libs.home_assistant_base import HomeAssistantDevice


class ClimateBedroom(HomeAssistantDevice):
    """
    A class for controlling bedroom climate devices using the Home Assistant Python API.

    Attributes:
        client (Client): Home Assistant API client instance.
        climate_entity_id (str): Entity ID for the bedroom climate device.
        entity_id_health_mode (str): Entity ID for the health mode switch.
        entity_id_fresh_air_mode (str): Entity ID for the fresh air mode switch.
        entity_id_quiet_mode (str): Entity ID for the quiet mode switch.
        entity_id_panel_light (str): Entity ID for the panel light switch.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the bedroom climate controller using the Home Assistant Python API.

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
                        "climate_bedroom": {
                            "entity_id": {
                                "climate": str,
                                "switch_health_mode": str,
                                "switch_fresh_air_mode": str,
                                "switch_quiet_mode": str,
                                "switch_panel_light": str
                            }
                        }
                    }
                }
        """
        super().__init__(config, "climate_bedroom")
        self.climate_entity_id = self.entity_ids["climate"]
        self.entity_id_health_mode = self.entity_ids["switch_health_mode"]
        self.entity_id_fresh_air_mode = self.entity_ids["switch_fresh_air_mode"]
        self.entity_id_quiet_mode = self.entity_ids["switch_quiet_mode"]
        self.entity_id_panel_light = self.entity_ids["switch_panel_light"]

    def fast_cool_mode(self, temperature: int = 25) -> None:
        """
        Activates the fast cool mode for the bedroom climate device.

        Args:
            temperature (int, optional): The desired temperature. Defaults to 25.
        """
        self.set_preset_mode("none")
        self.set_hvac_mode("cool")
        self.set_fan_mode("high")
        self.set_temperature(temperature)
        self.set_swing_mode("off")
        self.turn_off_health_mode()
        self.turn_off_fresh_air_mode()
        self.turn_off_quiet_mode()

    def set_preset_mode(self, preset_mode: str) -> None:
        """
        Sets the preset mode for the bedroom climate device.

        Args:
            preset_mode (str): The desired preset mode (e.g., 'none','eco','comfort').
        """
        self._call_service(
            "climate",
            "set_preset_mode",
            {"entity_id": self.climate_entity_id, "preset_mode": preset_mode},
        )

    def set_swing_mode(self, swing_mode: str) -> None:
        """
        Sets the swing mode for the bedroom climate device.

        Args:
            swing_mode (str): The desired swing mode (e.g., 'horizontal', 'vertical').
        """
        self._call_service(
            "climate",
            "set_swing_mode",
            {"entity_id": self.climate_entity_id, "swing_mode": swing_mode},
        )

    def set_temperature(self, temperature: int) -> None:
        """
        Sets the temperature for the bedroom climate device.

        Args:
            temperature (int): The desired temperature.
        """
        self._call_service(
            "climate",
            "set_temperature",
            {"entity_id": self.climate_entity_id, "temperature": temperature},
        )

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """
        Sets the HVAC mode for the bedroom climate device.

        Args:
            hvac_mode (str): The desired HVAC mode (e.g., 'cool', 'heat', 'off').
        """
        self._call_service(
            "climate",
            "set_hvac_mode",
            {"entity_id": self.climate_entity_id, "hvac_mode": hvac_mode},
        )

    def set_fan_mode(self, fan_mode: str) -> None:
        """
        Sets the fan mode for the bedroom climate device.

        Args:
            fan_mode (str): The desired fan mode (e.g., 'low', 'medium', 'high').
        """
        self._call_service(
            "climate",
            "set_fan_mode",
            {"entity_id": self.climate_entity_id, "fan_mode": fan_mode},
        )

    def turn_on_climate(self) -> None:
        """
        Turns on the bedroom climate device.
        """
        self._turn_on(self.climate_entity_id, "climate")

    def turn_off_climate(self) -> None:
        """
        Turns off the bedroom climate device.
        """
        self._turn_off(self.climate_entity_id, "climate")

    def switch_climate(self, value: bool) -> None:
        """
        Switches the bedroom climate device on or off based on the provided boolean value.

        Args:
            value (bool): If True, turns on the climate; if False, turns off the climate.
        """
        self._switch(self.climate_entity_id, value, "climate")

    def turn_on_panel_light(self) -> None:
        """
        Turns on the panel light for the bedroom climate device.
        """
        self._turn_on(self.entity_id_panel_light)

    def turn_off_panel_light(self) -> None:
        """
        Turns off the panel light for the bedroom climate device.
        """
        self._turn_off(self.entity_id_panel_light)

    def switch_panel_light(self, value: bool) -> None:
        """
        Switches the panel light for the bedroom climate device.

        Args:
            value (bool): If True, turns on the panel light; if False, turns off the panel light.
        """
        self._switch(self.entity_id_panel_light, value)

    def toggle_fresh_air_mode(self) -> None:
        """
        Toggles the fresh air mode for the bedroom climate device.
        """
        self._toggle(self.entity_id_fresh_air_mode)

    def turn_on_fresh_air_mode(self) -> None:
        """
        Turns on the fresh air mode for the bedroom climate device.
        """
        self._turn_on(self.entity_id_fresh_air_mode)

    def turn_off_fresh_air_mode(self) -> None:
        """
        Turns off the fresh air mode for the bedroom climate device.
        """
        self._turn_off(self.entity_id_fresh_air_mode)

    def switch_fresh_air_mode(self, value: bool) -> None:
        """
        Switches the fresh air mode for the bedroom climate device.

        Args:
            value (bool): If True, turns on the fresh air mode; if False, turns off the fresh air mode.
        """
        self._switch(self.entity_id_fresh_air_mode, value)

    def toggle_health_mode(self) -> None:
        """
        Toggles the health mode for the bedroom climate device.
        """
        self._toggle(self.entity_id_health_mode)

    def turn_on_health_mode(self) -> None:
        """
        Turns on the health mode for the bedroom climate device.
        """
        self._turn_on(self.entity_id_health_mode)

    def turn_off_health_mode(self) -> None:
        """
        Turns off the health mode for the bedroom climate device.
        """
        self._turn_off(self.entity_id_health_mode)

    def switch_health_mode(self, value: bool) -> None:
        """
        Switches the health mode for the bedroom climate device.

        Args:
            value (bool): If True, turns on the health mode; if False, turns off the health mode.
        """
        self._switch(self.entity_id_health_mode, value)

    def toggle_quiet_mode(self) -> None:
        """
        Toggles the quiet mode for the bedroom climate device.
        """
        self._toggle(self.entity_id_quiet_mode)

    def turn_on_quiet_mode(self) -> None:
        """
        Turns on the quiet mode for the bedroom climate device.
        """
        self._turn_on(self.entity_id_quiet_mode)

    def turn_off_quiet_mode(self) -> None:
        """
        Turns off the quiet mode for the bedroom climate device.
        """
        self._turn_off(self.entity_id_quiet_mode)

    def switch_quiet_mode(self, value: bool) -> None:
        """
        Switches the quiet mode for the bedroom climate device.

        Args:
            value (bool): If True, turns on the quiet mode; if False, turns off the quiet mode.
        """
        self._switch(self.entity_id_quiet_mode, value)

    def get_fresh_air_mode_state(self) -> bool:
        """
        Retrieves the state of the fresh air mode switch.
        Returns:
            bool: True if the fresh air mode is on, False otherwise.
        """
        return self._get_state(self.entity_id_fresh_air_mode)

    def get_health_mode_state(self) -> bool:
        """
        Retrieves the state of the health mode switch.
        Returns:
            bool: True if the health mode is on, False otherwise.
        """
        return self._get_state(self.entity_id_health_mode)

    def get_quiet_mode_state(self) -> bool:
        """
        Retrieves the state of the quiet mode switch.
        Returns:
            bool: True if the quiet mode is on, False otherwise.
        """
        return self._get_state(self.entity_id_quiet_mode)

    def get_panel_light_state(self) -> bool:
        """
        Retrieves the state of the panel light switch.
        Returns:
            bool: True if the panel light is on, False otherwise.
        """
        return self._get_state(self.entity_id_panel_light)

    def get_climate_state(self) -> Dict:
        """
        Retrieves the state of the bedroom climate device.
        Returns:
            Dict: The state of the bedroom climate device.
        """
        state_details = self._get_entity_state(self.climate_entity_id)
        return {
            "state": state_details.get("state"),
            "attributes": {
                "current_temperature": state_details.get("attributes", {}).get(
                    "current_temperature"
                ),
                "temperature": state_details.get("attributes", {}).get("temperature"),
                "preset_mode": state_details.get("attributes", {}).get("preset_mode"),
                "fan_mode": state_details.get("attributes", {}).get("fan_mode"),
                "swing_mode": state_details.get("attributes", {}).get("swing_mode"),
                "hvac_mode": state_details.get("attributes", {}).get("hvac_mode"),
            },
        }

    def get_states(self) -> Dict:
        """
        Retrieves the states of the bedroom climate device and its switches.
        Returns:
            Dict: The states of the bedroom climate device and its switches.
        """
        return {
            "climate": self.get_climate_state(),
            "fresh_air_mode": self.get_fresh_air_mode_state(),
            "health_mode": self.get_health_mode_state(),
            "quiet_mode": self.get_quiet_mode_state(),
            "panel_light": self.get_panel_light_state(),
        }
