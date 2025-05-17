import azure.cognitiveservices.speech as speechsdk
from concurrent.futures import ThreadPoolExecutor
from time import sleep
import asyncio
import websockets
import json
import datetime
import sys
from typing import *
from libs.bedroom_light import Light_bedroom
from libs.bedroom_climate import Climate_bedroom
from libs.websocket_client import Websocket_client_esp32


async def connect_to_server():
    uri = "ws://192.168.10.18/ws"


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
        for key in self.keyword_keep_alive_list:
            keyword_recognize = self.keyword_recognizers[key]
            keyword_recognize["recognizer"].recognize_once_async(
                keyword_recognize["model"]
            )

    def activate_all_keyword_recogizers(self):
        for keyword, items in self.keyword_recognizers.items():
            if keyword not in self.keyword_keep_alive_list:
                items["recognizer"].recognize_once_async(items["model"])
        self.response_time_counter = self.response_timeout

    def stop_all_keyword_recogizers(self):
        for keyword, items in self.keyword_recognizers.items():
            items["recognizer"].stop_recognition_async().get()

    async def stop_keyword_recogizers(self):
        interval = 1
        while True:
            if self.response_time_counter > 0:
                while self.response_time_counter > 0:
                    self.response_time_counter -= interval
                    print("self.response_time_counter:", self.response_time_counter)
                    await asyncio.sleep(interval)
                for keyword, items in self.keyword_recognizers.items():
                    if keyword not in self.keyword_keep_alive_list:
                        items["recognizer"].stop_recognition_async().get()
            await asyncio.sleep(interval)

    def __init__(self, configure_path: str):
        with open(configure_path, mode="r", encoding="utf-8") as f:
            self.configure = json.load(f)
        self.light_bedroom = Light_bedroom(self.configure)
        self.climate_bedroom = Climate_bedroom(self.configure)
        self.esp32_config = self.configure["esp32"]
        self.esp32_bedroom_config = self.esp32_config["bedroom"]
        self.ws_client_esp32 = Websocket_client_esp32(self.esp32_bedroom_config["uri"])
        # self.turn_on_light_keyword_recognizer.stop_recognition_async().get()
        self.response_timeout = 10
        self.response_time_counter = 0
        self.keyword_keep_alive_list = ["ai_name", "turn_on_light"]
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
                "callback_recognized": self.climate_bedroom.turn_on_climate,
            },
            "turn_off_cliamte": {
                "keyword": "关闭空调",
                "model_file": "./voices/models/turn-off-climate.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.climate_bedroom.turn_off_climate,
            },
            "ai_name": {
                "keyword": "千夏",
                "model_file": "./voices/models/qianxia.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": self.activate_all_keyword_recogizers,
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

        return recognized_keyword_cb

    async def data_generation_task(self):
        while True:
            result = await self.ws_client_esp32.get_temperature_humidity()
            if result:
                print(f'{result["temperature"]},{result["humidity"]}')
            else:
                print("Timeout...")
            await asyncio.sleep(5)

    # 同步任务示例 - 在单独线程中运行
    def sync_task(self, stop_event: asyncio.Event):
        """在单独线程中运行的同步任务示例"""
        print("同步任务已启动")
        while not stop_event.is_set():
            print("同步任务正在运行...")
            sleep(6)
        print("同步任务已停止")

    # 主函数 - 协调所有任务
    async def main(self):
        # 创建线程池和停止事件
        stop_event = asyncio.Event()
        executor = ThreadPoolExecutor(max_workers=1)

        # 创建并启动所有任务
        loop = asyncio.get_running_loop()
        await self.ws_client_esp32.connect()
        tasks = [
            self.data_generation_task(),  # 数据生成任务
            self.stop_keyword_recogizers(),
            self.ws_client_esp32.receive_messages(),  # WebSocket消息接收任务
            self.ws_client_esp32.heartbeat_task(),  # 心跳任务
            loop.run_in_executor(executor, self.sync_task, stop_event),  # 同步任务
        ]

        # 运行所有任务，直到其中一个完成或被取消
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("程序被用户中断")
        finally:
            # 清理资源
            await self.ws_client_esp32.close()
            stop_event.set()
            executor.shutdown()


AI = AI_Server(configure_path="./configure.json")

if __name__ == "__main__":
    # 启动主事件循环
    asyncio.run(AI.main())
