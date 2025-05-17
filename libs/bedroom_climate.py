from requests import post
from typing import *


class Climate_bedroom:
    def __init__(self, configure: Dict):
        self.ha_config = configure["home_assistant"]
        self.climate_config = configure["smart_home_appliances"]["climate_bedroom"]
        self.light_config = configure["smart_home_appliances"]["light_bedroom"]
        self.ha_url = "http://" + self.ha_config["host"] + ":" + self.ha_config["port"]
        self.api_url = self.ha_url + "/api/services"
        self.headers = {
            "Authorization": "Bearer " + self.ha_config["long_lived_access_token"],
            "content-type": "application/json",
        }
        self.url_trun_off_climate = self.api_url + "/climate/turn_off"
        self.url_trun_on_climate = self.api_url + "/climate/turn_on"
        self.url_set_humidity = self.api_url + "/climate/set_humidity"
        self.climate_entity_id = self.climate_config["entity_id_climate"]

    def turn_on_climate(self):
        json = {"entity_id": self.climate_entity_id}
        response = post(self.url_trun_on_climate, headers=self.headers, json=json)
        print(response.text)

    def turn_off_climate(self):
        json = {"entity_id": self.climate_entity_id}
        response = post(self.url_trun_off_climate, headers=self.headers, json=json)
        print(response.text)

    def set_humidity(self, humidity: int):
        json = {"entity_id": self.climate_entity_id, "humidity": humidity}
        response = post(self.url_set_humidity, headers=self.headers, json=json)
        print(response.text)
