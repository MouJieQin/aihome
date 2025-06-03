"""
This module provides an `ElecMeterController` class for controlling an electricity meter
using the Home Assistant Python API. It allows users to turn the controller on/off and
retrieve the state of the controller switch.
"""

from typing import Dict, Any
from libs.home_assistant_base import HomeAssistantDevice


class ElecMeterController(HomeAssistantDevice):
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
        HomeAssistantDevice.__init__(self, config, "elec_meter_controller")
        # Get the entity ID for the controller switch status
        self.switch_status_entity_id = self.entity_ids["switch_status"]

    def turn_on_controller(self) -> None:
        """
        Turns on the electricity meter controller by calling the Home Assistant `switch.turn_on` service.
        """
        self._turn_on(self.switch_status_entity_id)

    def turn_off_controller(self) -> None:
        """
        Turns off the electricity meter controller by calling the Home Assistant `switch.turn_off` service.
        """
        self._turn_off(self.switch_status_entity_id)

    def switch_controller(self, value: bool) -> None:
        """
        Switches the electricity meter controller on or off based on the provided value.
        Args:
            value (bool): If True, turns on the controller. If False, turns off the controller.
        """
        self._switch(self.switch_status_entity_id, value)

    def get_state_controller_switch(self) -> bool:
        """
        Retrieves the state of the electricity meter controller switch.

        Returns:
            Dict: The state of the controller switch.
        """
        return self._get_state(self.switch_status_entity_id)
