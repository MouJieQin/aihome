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
        self._call_service(
            "climate",
            "set_preset_mode",
            {"entity_id": self.climate_entity_id, "preset_mode": "none"},
        )
        self._call_service(
            "climate",
            "set_hvac_mode",
            {"entity_id": self.climate_entity_id, "hvac_mode": "cool"},
        )
        self._call_service(
            "climate",
            "set_fan_mode",
            {"entity_id": self.climate_entity_id, "fan_mode": "high"},
        )
        self._call_service(
            "climate",
            "set_temperature",
            {"entity_id": self.climate_entity_id, "temperature": temperature},
        )
        self._call_service(
            "climate",
            "set_swing_mode",
            {"entity_id": self.climate_entity_id, "swing_mode": "off"},
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

    def toggle_fresh_air_mode(self) -> None:
        """
        Toggles the fresh air mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "toggle", {"entity_id": self.entity_id_fresh_air_mode}
        )

    def toggle_health_mode(self) -> None:
        """
        Toggles the health mode for the bedroom climate device.
        """
        self._call_service(
            "switch", "toggle", {"entity_id": self.entity_id_health_mode}
        )

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

    def get_entity_state(self, entity_id: str) -> Dict:
        """
        Retrieves the state of a specified entity.

        Args:
            entity_id (str): The ID of the entity.

        Returns:
            Dict: The state of the entity.
        """
        try:
            state = self.client.get_state(entity_id)
            return state
        except Exception as e:
            logger.exception(e)
            return {}


# configure = {}
# import json

# with open("./configure.json", mode="r", encoding="utf-8") as f:
#     configure = json.load(f)
# x = ClimateBedroom(configure)
# x.fast_cool_mode()
