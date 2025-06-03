"""
This module provides a `ClimateBedroom` class for controlling bedroom climate devices
using the Home Assistant Python API. It allows users to perform various operations
such as turning the climate device on/off, switching modes, and setting temperature.
"""

from homeassistant_api import Client
from typing import Dict, Any
from libs.log_config import logger


class ClimateBedroom:
    """
    A class for controlling bedroom climate devices using the Home Assistant Python API.

    Attributes:
        client (Client): Home Assistant API client instance.
        climate_entity_id (str): Entity ID for the bedroom climate device.
        entity_id_health_mode (str): Entity ID for the health mode switch.
        entity_id_fresh_air_mode (str): Entity ID for the fresh air mode switch.
        entity_id_quiet_mode (str): Entity ID for the quiet mode switch.
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
                                "switch_quiet_mode": str
                            }
                        }
                    }
                }
        """
        ha_config = config["home_assistant"]
        climate_config = config["smart_home_appliances"]["climate_bedroom"]
        api_url = f"http://{ha_config['host']}:{ha_config['port']}/api"
        self.client = Client(api_url, ha_config["long_lived_access_token"])
        self.climate_entity_id = climate_config["entity_id"]["climate"]
        self.entity_id_health_mode = climate_config["entity_id"]["switch_health_mode"]
        self.entity_id_fresh_air_mode = climate_config["entity_id"][
            "switch_fresh_air_mode"
        ]
        self.entity_id_quiet_mode = climate_config["entity_id"]["switch_quiet_mode"]
        self.entity_id_panel_light = climate_config["entity_id"]["switch_panel_light"]

    def _call_service(self, domain: str, service: str, data: Dict[str, Any]) -> None:
        """
        Calls a Home Assistant service.

        Args:
            domain (str): The domain of the service (e.g., 'climate', 'switch').
            service (str): The name of the service (e.g., 'turn_on', 'set_temperature').
            data (Dict[str, Any]): The data to pass to the service.
        """
        try:
            res = self.client.trigger_service(domain, service, **data)
            logger.info(res)
        except Exception as e:
            logger.exception(e)

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
        self._call_service("climate", "turn_on", {"entity_id": self.climate_entity_id})

    def turn_off_climate(self) -> None:
        """
        Turns off the bedroom climate device.
        """
        self._call_service("climate", "turn_off", {"entity_id": self.climate_entity_id})

    def switch_climate(self, value: bool) -> None:
        """
        Switches the bedroom climate device on or off based on the provided boolean value.
        Args:
            value (bool): If True, turns on the climate; if False, turns off the climate.
        """
        if value:
            self.turn_on_climate()
        else:
            self.turn_off_climate()

    def turn_on_panel_light(self) -> None:
        """
        Turns on the panel light for the bedroom climate device.
        """
        self._call_service(
            "switch", "turn_on", {"entity_id": self.entity_id_panel_light}
        )

    def turn_off_panel_light(self) -> None:
        """
        Turns off the panel light for the bedroom climate device.
        """
        self._call_service(
            "switch", "turn_off", {"entity_id": self.entity_id_panel_light}
        )

    def switch_panel_light(self, value: bool) -> None:
        """
        Switches the panel light for the bedroom climate device.
        Args:
            value (bool): If True, turns on the panel light; if False, turns off the panel light.
        """
        if value:
            self.turn_on_panel_light()
        else:
            self.turn_off_panel_light()

    def toggle_fresh_air_mode(self) -> None:
        """
        Toggles the fresh air mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "toggle", {"entity_id": self.entity_id_fresh_air_mode}
        )

    def turn_on_fresh_air_mode(self) -> None:
        """
        Turns on the fresh air mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "turn_on", {"entity_id": self.entity_id_fresh_air_mode}
        )

    def turn_off_fresh_air_mode(self) -> None:
        """
        Turns off the fresh air mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "turn_off", {"entity_id": self.entity_id_fresh_air_mode}
        )

    def switch_fresh_air_mode(self, value: bool) -> None:
        """
        Switches the fresh air mode for the bedroom climate device.
        Args:
            value (bool): If True, turns on the fresh air mode; if False, turns off the fresh air mode.
        """
        if value:
            self.turn_on_fresh_air_mode()
        else:
            self.turn_off_fresh_air_mode()

    def toggle_health_mode(self) -> None:
        """
        Toggles the health mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "toggle", {"entity_id": self.entity_id_health_mode}
        )

    def turn_on_health_mode(self) -> None:
        """
        Turns on the health mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "turn_on", {"entity_id": self.entity_id_health_mode}
        )

    def turn_off_health_mode(self) -> None:
        """
        Turns off the health mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "turn_off", {"entity_id": self.entity_id_health_mode}
        )

    def switch_health_mode(self, value: bool) -> None:
        """
        Switches the health mode for the bedroom climate device.
        Args:
            value (bool): If True, turns on the health mode; if False, turns off the health mode.
        """
        if value:
            self.turn_on_health_mode()
        else:
            self.turn_off_health_mode()

    def toggle_quiet_mode(self) -> None:
        """
        Toggles the quiet mode for the bedroom climate device.
        """
        self._call_service("switch", "toggle", {"entity_id": self.entity_id_quiet_mode})

    def turn_on_quiet_mode(self) -> None:
        """
        Turns on the quiet mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "turn_on", {"entity_id": self.entity_id_quiet_mode}
        )

    def turn_off_quiet_mode(self) -> None:
        """
        Turns off the quiet mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "turn_off", {"entity_id": self.entity_id_quiet_mode}
        )

    def switch_quiet_mode(self, value: bool) -> None:
        """
        Switches the quiet mode for the bedroom climate device.
        Args:
            value (bool): If True, turns on the quiet mode; if False, turns off the quiet mode.
        """
        if value:
            self.turn_on_quiet_mode()
        else:
            self.turn_off_quiet_mode()

    def get_entity_state(self, entity_id: str) -> Dict:
        """
        Retrieves the state of a specified entity.

        Args:
            entity_id (str): The ID of the entity.

        Returns:
            Dict: The state of the entity.
        """
        try:
            state = self.client.get_state(entity_id)  # type: ignore
            return state
        except Exception as e:
            logger.exception(e)
            return {}
