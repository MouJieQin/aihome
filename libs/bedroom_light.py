from requests import post
from typing import *


class Light_bedroom:
    def __init__(self, configure: Dict):
        self.ha_config = configure["home_assistant"]
        self.light_config = configure["smart_home_appliances"]["light_bedroom"]
        self.ha_url = "http://" + self.ha_config["host"] + ":" + self.ha_config["port"]
        self.api_url = self.ha_url + "/api/services"
        self.url_trun_off_light = self.api_url + "/light/turn_off"
        self.url_trun_on_light = self.api_url + "/light/turn_on"
        self.url_number_fan_speed = self.api_url + "/number/set_value"
        self.headers = {
            "Authorization": "Bearer " + self.ha_config["long_lived_access_token"],
            "content-type": "application/json",
        }
        self.light_entity_id = self.light_config["entity_id_light"]
        self.fan_speed_entity_id = self.light_config["entity_id_fan_speed"]

    def turn_on_light(self):
        json = {"entity_id": self.light_entity_id}
        response = post(self.url_trun_on_light, headers=self.headers, json=json)
        print(response.text)

    def turn_off_light(self):
        json = {"entity_id": self.light_entity_id}
        response = post(self.url_trun_off_light, headers=self.headers, json=json)
        print(response.text)

    def turn_on_light_mode_night(self):
        json_light_mode_night = {
            "entity_id": self.light_entity_id,
            "effect": "Night Light",
        }
        response = post(
            self.url_trun_on_light, headers=self.headers, json=json_light_mode_night
        )
        print(response.text)

    def turn_on_light_mode_movie(self):
        json_light_mode_movie = {
            "entity_id": self.light_entity_id,
            "effect": "Cinema Mode",
        }
        response = post(
            self.url_trun_on_light, headers=self.headers, json=json_light_mode_movie
        )
        print(response.text)

    def turn_on_light_mode_entertainment(self):
        json_light_mode_entertainment = {
            "entity_id": self.light_entity_id,
            "effect": "Entertainment Mode",
        }
        response = post(
            self.url_trun_on_light,
            headers=self.headers,
            json=json_light_mode_entertainment,
        )
        print(response.text)

    def turn_on_light_mode_reception(self):
        json_light_mode_reception = {
            "entity_id": self.light_entity_id,
            "effect": "Reception Mode",
        }
        response = post(
            self.url_trun_on_light,
            headers=self.headers,
            json=json_light_mode_reception,
        )
        print(response.text)

    def adjust_fan_speed(self, value: int):
        json = {
            "entity_id": self.fan_speed_entity_id,
            "value": value,
        }
        response = post(self.url_number_fan_speed, headers=self.headers, json=json)
        print(response.text)

    def adjust_fan_speed_to_max(self):
        self.adjust_fan_speed(100)

    def adjust_fan_speed_to_min(self):
        self.adjust_fan_speed(1)

    def adjust_fan_speed_to_fourth(self):
        self.adjust_fan_speed(69)
