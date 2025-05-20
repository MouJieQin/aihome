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
        self.url_toggle_switch = self.api_url + "/switch/toggle"
        self.url_trun_on_switch = self.api_url + "/switch/turn_on"
        self.url_trun_off_switch = self.api_url + "/switch/turn_off"
        self.url_set_humidity = self.api_url + "/climate/set_humidity"
        self.climate_entity_id = self.climate_config["entity_id"]
        self.entity_id_climate = self.climate_entity_id["climate"]
        self.entity_id_health_mode = self.climate_entity_id["switch_health_mode"]
        self.entity_id_fresh_air_mode = self.climate_entity_id["switch_fresh_air_mode"]
        self.entity_id_quiet_mode = self.climate_entity_id["switch_quiet_mode"]

    def turn_on_climate(self):
        json = {"entity_id": self.entity_id_climate}
        response = post(self.url_trun_on_climate, headers=self.headers, json=json)
        print(response.text)

    def turn_off_climate(self):
        json = {"entity_id": self.entity_id_climate}
        response = post(self.url_trun_off_climate, headers=self.headers, json=json)
        print(response.text)

    def toggle_fresh_air_mode(self):
        json = {"entity_id": self.entity_id_fresh_air_mode}
        response = post(self.url_toggle_switch, headers=self.headers, json=json)
        print(response.text)

    def toggle_health_mode(self):
        json = {"entity_id": self.entity_id_health_mode}
        response = post(self.url_toggle_switch, headers=self.headers, json=json)
        print(response.text)

    def toggle_quiet_mode(self):
        json = {"entity_id": self.entity_id_quiet_mode}
        response = post(self.url_toggle_switch, headers=self.headers, json=json)
        print(response.text)

    def turn_on_health_mode(self):
        json = {"entity_id": self.entity_id_health_mode}
        response = post(self.url_trun_on_switch, headers=self.headers, json=json)
        print(response.text)

    def turn_off_health_mode(self):
        json = {"entity_id": self.entity_id_health_mode}
        response = post(self.url_trun_off_switch, headers=self.headers, json=json)
        print(response.text)

    # def set_humidity(self, humidity: int):
    #     json = {"entity_id": self.entity_id_climate, "humidity": humidity}
    #     response = post(self.url_set_humidity, headers=self.headers, json=json)
    #     print(response.text)


# configure = {}
# import json

# with open("./configure.json", mode="r", encoding="utf-8") as f:
#     configure = json.load(f)
# x = Climate_bedroom(configure)
# x.turn_off_climate()
