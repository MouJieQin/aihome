from typing import Dict, Any
from libs.home_assistant_base import HomeAssistantDevice


class HomeAssistantSensors(HomeAssistantDevice):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "sensors")
        self.dht22_humidity_entity_id = self.entity_ids["dht22_humidity"]
        self.dht22_humidity_average_entity_id = self.entity_ids[
            "dht22_humidity_average"
        ]
        self.dht22_humidity_standard_deviation = self.entity_ids[
            "dht22_humidity_standard_deviation"
        ]
        self.dht22_temperature_entity_id = self.entity_ids["dht22_temperature"]
        self.dht22_temperature_average_entity_id = self.entity_ids[
            "dht22_temperature_average"
        ]
        self.dht22_temperature_standard_deviation = self.entity_ids[
            "dht22_temperature_standard_deviation"
        ]
        self.ze08_ch2o_entity_id = self.entity_ids["ze08_ch2o"]
        self.ze08_ch2o_average_entity_id = self.entity_ids["ze08_ch2o_average"]
        self.ze08_ch2o_standard_deviation = self.entity_ids[
            "ze08_ch2o_standard_deviation"
        ]

    def get_dht22_humidity_average_state(self) -> Dict:
        """
        Retrieves the state of the dht22 humidity average.
        """
        state_details = self._get_entity_state(self.dht22_humidity_average_entity_id)
        return {"state": state_details.get("state")}

    def get_dht22_temperature_average(self) -> Dict:
        """
        Retrieves the state of the dht22 temperature average.
        """
        state_details = self._get_entity_state(self.dht22_temperature_average_entity_id)
        return {"state": state_details.get("state")}

    def get_ze08_ch2o_average(self) -> Dict:
        """
        Retrieves the state of the ze08 ch2o average.
        """
        state_details = self._get_entity_state(self.ze08_ch2o_average_entity_id)
        if state_details.get("state") == "unknown":
            state_details = self._get_entity_state(self.ze08_ch2o_entity_id)
        return {
            "state": state_details.get("state"),
            "unit_of_measurement": state_details.get("attributes", {}).get(
                "unit_of_measurement"
            ),
        }

    def get_states(self) -> Dict:
        """
        Retrieves the states of the sensors.
        """
        return {
            "dht22_humidity": self.get_dht22_humidity_average_state(),
            "dht22_temperature": self.get_dht22_temperature_average(),
            "ze08_ch2o": self.get_ze08_ch2o_average(),
        }
