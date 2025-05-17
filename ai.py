import azure.cognitiveservices.speech as speechsdk
from time import sleep
import asyncio
import websockets
import json
import datetime
import sys
from typing import *
from libs.bedroom_light import Light_bedroom
from libs.bedroom_climate import Climate_bedroom

# async def connect_to_server():
#     uri = "ws://192.168.10.18/ws"
#     record = []
#     async with websockets.connect(uri) as websocket:
#         while True:
#             # 发送消息
#             try:
#                 message = {}
#                 message["from"] = "AI_server"
#                 message["to"] = "esp32_sensors"
#                 message["type"] = "humidity_temperature"
#                 txt_message = json.dumps(message, ensure_ascii=False)
#                 await websocket.send(txt_message)
#                 # print(f"Sent message: {txt_message}")

#                 # 接收服务器的响应
#                 txt_message = await websocket.recv()
#                 # print(f"Received response: {txt_message}")
#                 message = json.loads(txt_message)
#                 if message["from"] == "esp32_sensors":
#                     if message["type"] == "humidity_temperature":
#                         # record.append({"time":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                         #             "humidity":message["humidity"],"temperature":message["temperature"] })
#                         # print(record)
#                         # with open("th.log", mode="w", encoding="utf-8") as f:
#                         #     f.write(json.dumps(record), ensure_ascii=False, indent=4)
#                         print(
#                             datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                             "   Temperature: {}℃   Humidity: {}%".format(
#                                 message["temperature"], message["humidity"]
#                             ),
#                         )
#                         sys.stdout.flush()
#                 await asyncio.sleep(58)
#             except Exception as e:
#                 print(e)
#                 await websocket.close()


# # 运行事件循环连接到WebSocket服务器
# asyncio.get_event_loop().run_until_complete(connect_to_server())
# exit(0)


class AI_Server:
    def _keyword_recognizers_setup(self):
        for keyword, items in self.keyword_recognizers.items():
            items["model"] = speechsdk.KeywordRecognitionModel(items["model_file"])
            items["recognizer"] = speechsdk.KeywordRecognizer()
            items["recognized_keyword_cb"] = AI_Server._recognized_keyword_cb(
                items["keyword"],
                items["recognizer"],
                items["model"],
                items["callback_recognized"],
            )
            items["recognizer"].recognized.connect(items["recognized_keyword_cb"])
            items["recognized_keyword_cb"] = AI_Server._canceled_keyword_cb(
                items["keyword"]
            )
            items["recognizer"].canceled.connect(items["recognized_keyword_cb"])
            items["recognizer"].recognize_once_async(items["model"])

    def __init__(self, configure_path: str):
        with open(configure_path, mode="r", encoding="utf-8") as f:
            self.configure = json.load(f)
        self.light_bedroom = Light_bedroom(self.configure)
        self.climate_bedroom = Climate_bedroom(self.configure)
        # self.turn_on_light_keyword_recognizer.stop_recognition_async().get()
        self.keyword_recognizers = {
            "turn_on_light": {
                "keyword": "开灯",
                "model_file": "./voices/models/19f55a72-5f72-4334-8e0b-1ae922002559.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.light_bedroom.turn_on_light,
            },
            "turn_off_light": {
                "keyword": "关灯",
                "model_file": "./voices/models/5b1c6dc0-7987-4954-896e-9630b6cbcca9.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.light_bedroom.turn_off_light,
            },
            "fan_speed_max": {
                "keyword": "最大风速",
                "model_file": "./voices/models/8c3db10e-d572-419a-afc7-b47cd0cb6c86.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.light_bedroom.adjust_fan_speed_to_max,
            },
            "fan_speed_fourth": {
                "keyword": "四级风速",
                "model_file": "./voices/models/fan-speed-fourth.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.light_bedroom.adjust_fan_speed_to_fourth,
            },
            "fan_speed_one": {
                "keyword": "一级风速",
                "model_file": "./voices/models/fan-speed-one.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.light_bedroom.adjust_fan_speed_to_min,
            },
            "light_mode_movie": {
                "keyword": "影院模式",
                "model_file": "./voices/models/light-mode-movie.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.light_bedroom.turn_on_light_mode_movie,
            },
            "light_mode_entertainment": {
                "keyword": "娱乐模式",
                "model_file": "./voices/models/light-mode-entertainment.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.light_bedroom.turn_on_light_mode_entertainment,
            },
            "light_mode_reception": {
                "keyword": "会客模式",
                "model_file": "./voices/models/light-mode-reception.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.light_bedroom.turn_on_light_mode_reception,
            },
            "light_mode_night": {
                "keyword": "夜灯模式",
                "model_file": "./voices/models/light-mode-night.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.light_bedroom.turn_on_light_mode_night,
            },
            "turn_on_cliamte": {
                "keyword": "开启空调",
                "model_file": "./voices/models/turn-on-climate.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": lambda: self.climate_bedroom.turn_on_climate,
            },
            "turn_off_cliamte": {
                "keyword": "关闭空调",
                "model_file": "./voices/models/turn-off-climate.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": lambda: self.climate_bedroom.turn_off_climate,
            },
            "ai_name": {
                "keyword": "千夏",
                "model_file": "./voices/models/qianxia.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": lambda: "千夏",
            },
        }
        self._keyword_recognizers_setup()

    @staticmethod
    def _canceled_keyword_cb(keyword: str) -> Callable:
        def canceled_keyword_cb(evt):
            result = evt.result
            if result.reason == speechsdk.ResultReason.Canceled:
                print(f"{keyword} CANCELED: {result.cancellation_details.reason}")

        return canceled_keyword_cb

    @staticmethod
    def _recognized_keyword_cb(
        keyword: str,
        recognizer: speechsdk.KeywordRecognizer,
        keyword_model: speechsdk.KeywordRecognitionModel,
        callback: Callable,
    ):
        def recognized_keyword_cb(evt):
            result = evt.result
            if result.reason == speechsdk.ResultReason.RecognizedKeyword:
                print("RECOGNIZED KEYWORD: {}".format(result.text))
                callback()
                # to recognize keyword again.
                recognizer.recognize_once_async(keyword_model)
                # recognizer.stop_recognition_async().get()

        return recognized_keyword_cb


AI = AI_Server(configure_path="./configure.json")
print("start sleep...")
while True:
    sleep(5)
