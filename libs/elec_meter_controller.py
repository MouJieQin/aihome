"""
This module provides an `ElecMeterController` class for controlling an electricity meter
using the Home Assistant Python API. It allows users to turn the controller on/off and
retrieve the state of the controller switch.
"""

from homeassistant_api import Client
from typing import Dict, Any
from libs.log_config import logger


class ElecMeterController:
    """
    A class for controlling an electricity meter using the Home Assistant Python API.

    Attributes:
        client (Client): Home Assistant API client instance.
        switch_status_entity_id (str): Entity ID for the controller switch status.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the electricity meter controller using the Home Assistant Python API.

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
                        "elec_meter_controller": {
                            "entity_id": {
                                "switch_status": str
                            }
                        }
                    }
                }
        """
        # Extract Home Assistant configuration
        ha_config = config["home_assistant"]
        # Extract electricity meter controller configuration
        controller_config = config["smart_home_appliances"]["elec_meter_controller"]
        # Construct the API URL
        api_url = f"http://{ha_config['host']}:{ha_config['port']}/api"
        # Initialize the Home Assistant client
        self.client = Client(api_url, ha_config["long_lived_access_token"])
        # Get the entity ID for the controller switch status
        self.switch_status_entity_id = controller_config["entity_id"]["switch_status"]

    def _call_service(self, domain: str, service: str, data: Dict[str, Any]) -> None:
        """
        Calls a Home Assistant service.

        Args:
            domain (str): The domain of the service (e.g., 'switch', 'light').
            service (str): The name of the service (e.g., 'turn_on', 'turn_off').
            data (Dict[str, Any]): The data to pass to the service.
        """
        try:
            # Trigger the Home Assistant service
            res = self.client.trigger_service(domain, service, **data)
            # Log the service call response
            logger.info(res)
        except Exception as e:
            # Log any exceptions that occur during the service call
            logger.exception(e)

    def turn_on_controller(self) -> None:
        """
        Turns on the electricity meter controller by calling the Home Assistant `switch.turn_on` service.
        """
        # Bug fix: Change domain from 'light' to 'switch'
        self._call_service(
            "switch", "turn_on", {"entity_id": self.switch_status_entity_id}
        )

    def turn_off_controller(self) -> None:
        """
        Turns off the electricity meter controller by calling the Home Assistant `switch.turn_off` service.
        """
        # Bug fix: Change domain from 'light' to 'switch'
        self._call_service(
            "switch", "turn_off", {"entity_id": self.switch_status_entity_id}
        )

    def switch_controller(self, value: bool) -> None:
        """
        Switches the electricity meter controller on or off based on the provided value.
        Args:
            value (bool): If True, turns on the controller. If False, turns off the controller.
        """
        if value:
            self.turn_on_controller()
        else:
            self.turn_off_controller()

    def get_state_controller_switch(self) -> bool:
        """
        Retrieves the state of the electricity meter controller switch.

        Returns:
            Dict: The state of the controller switch.
        """
        state = self.client.get_state(entity_id=self.switch_status_entity_id)
        return state.state == "on"
