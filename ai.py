import azure.cognitiveservices.speech as speechsdk
from concurrent.futures import ThreadPoolExecutor
import pvporcupine
import pyaudio
import struct
from time import sleep
import asyncio
import json
import datetime
import threading
import sys
import os
import logging
from typing import *
from libs.bedroom_light import Light_bedroom
from libs.bedroom_climate import Climate_bedroom
from libs.websocket_client import Websocket_client_esp32
from libs.speaker import Speaker

os.chdir(os.path.dirname(__file__))

logging.basicConfig(
    filename="./run.log",
    format="%(asctime)s - %(name)s - %(levelname)s -%(module)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=20,
)


class AI_Server:
    response_timeout = 10
    response_time_counter = 0

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
        # for key in self.keyword_keep_alive_list:
        #     keyword_recognize = self.keyword_recognizers[key]
        #     keyword_recognize["recognizer"].recognize_once_async(
        #         keyword_recognize["model"]
        #     )

    def activate_all_keyword_recogizers(self):
        for keyword, items in self.keyword_recognizers.items():
            if keyword not in self.keyword_keep_alive_list:
                items["recognizer"].recognize_once_async(items["model"])
        AI_Server.response_time_counter = AI_Server.response_timeout
        self.speaker.play_start_record()

    def activate_response_keyword_recogizers(self):
        for keyword in self.keyword_keep_alive_list:
            item = self.keyword_recognizers[keyword]
            item["recognizer"].recognize_once_async(item["model"])
        AI_Server.response_time_counter = AI_Server.response_timeout
        self.speaker.play_start_record()

    def stop_all_keyword_recogizers(self):
        for keyword, items in self.keyword_recognizers.items():
            items["recognizer"].stop_recognition_async().get()

    async def stop_keyword_recogizers(self):
        interval = 1
        while True:
            if AI_Server.response_time_counter > 0:
                while AI_Server.response_time_counter > 0:
                    AI_Server.response_time_counter -= interval
                    print(
                        "AI_Server.response_time_counter:",
                        AI_Server.response_time_counter,
                    )
                    await asyncio.sleep(interval)
                for keyword, items in self.keyword_recognizers.items():
                    if keyword not in self.keyword_keep_alive_list:
                        items["recognizer"].stop_recognition_async().get()
                self.speaker.play_end_record()
            await asyncio.sleep(interval)

    def __init_porcupine(self):
        config_porcupine = self.configure["porcupine"]
        self.porcupine = pvporcupine.create(
            access_key=config_porcupine["access_key"],
            model_path=config_porcupine["model_path"],
            keyword_paths=[config_porcupine["keyword_paths"]],
        )
        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length,
        )
        self._ai_awake()

    def _ai_awake(self) -> threading.Thread:
        def run_ai_awake():
            while True:
                # 读取音频数据
                pcm = self.audio_stream.read(
                    self.porcupine.frame_length, exception_on_overflow=False
                )
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                # 处理音频并检测唤醒词
                result = self.porcupine.process(pcm)
                # 如果检测到唤醒词
                if result >= 0:
                    print(f"检测到唤醒词: あすな")
                    self.activate_all_keyword_recogizers()

        thread = threading.Thread(target=run_ai_awake)
        thread.daemon = True
        thread.start()
        return thread

    def _close_porcupine(self):
        if self.porcupine is not None:
            self.porcupine.delete()

        if self.audio_stream is not None:
            self.audio_stream.close()

        if self.pa is not None:
            self.pa.terminate()

    def __init__(self, configure_path: str):
        with open(configure_path, mode="r", encoding="utf-8") as f:
            self.configure = json.load(f)
        self.__init_porcupine()
        self.response_user = None
        self.callback_to_response_yes: Callable = None
        self.callback_to_response_no: Callable = None
        self.light_bedroom = Light_bedroom(self.configure)
        self.climate_bedroom = Climate_bedroom(self.configure)
        self.esp32_config = self.configure["esp32"]
        self.esp32_bedroom_config = self.esp32_config["bedroom"]
        self.ws_client_esp32 = Websocket_client_esp32(self.esp32_bedroom_config["uri"])
        self.speaker = Speaker(self.configure)
        self.keyword_keep_alive_list = ["response_no", "response_yes"]
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
                "callback_recognized": self.light_bedroom.turn_off_light,
            },
            "turn_off_fan": {
                "keyword": "关闭风扇",
                "model_file": "./voices/models/turn-off-fan.table",
                "callback_recognized": self.light_bedroom.turn_off_fan,
            },
            "fan_speed_max": {
                "keyword": "最大风速",
                "model_file": "./voices/models/8c3db10e-d572-419a-afc7-b47cd0cb6c86.table",
                "callback_recognized": self.light_bedroom.adjust_fan_speed_to_max,
            },
            "fan_speed_fourth": {
                "keyword": "四级风速",
                "model_file": "./voices/models/fan-speed-fourth.table",
                "callback_recognized": self.light_bedroom.adjust_fan_speed_to_fourth,
            },
            "fan_speed_one": {
                "keyword": "一级风速",
                "model_file": "./voices/models/fan-speed-one.table",
                "callback_recognized": self.light_bedroom.adjust_fan_speed_to_min,
            },
            "light_mode_movie": {
                "keyword": "影院模式",
                "model_file": "./voices/models/light-mode-movie.table",
                "callback_recognized": self.light_bedroom.turn_on_light_mode_movie,
            },
            "light_mode_entertainment": {
                "keyword": "娱乐模式",
                "model_file": "./voices/models/light-mode-entertainment.table",
                "callback_recognized": self.light_bedroom.turn_on_light_mode_entertainment,
            },
            "light_mode_reception": {
                "keyword": "会客模式",
                "model_file": "./voices/models/light-mode-reception.table",
                "callback_recognized": self.light_bedroom.turn_on_light_mode_reception,
            },
            "light_mode_night": {
                "keyword": "夜灯模式",
                "model_file": "./voices/models/light-mode-night.table",
                "callback_recognized": self.light_bedroom.turn_on_light_mode_night,
            },
            "turn_on_cliamte": {
                "keyword": "开启空调",
                "model_file": "./voices/models/turn-on-climate.table",
                "callback_recognized": lambda: self.auto_cool_mode(
                    temperature=25, total_simples=18
                ),
            },
            "turn_off_cliamte": {
                "keyword": "关闭空调",
                "model_file": "./voices/models/turn-off-climate.table",
                "callback_recognized": self.climate_bedroom.turn_off_climate,
            },
            "toggle_fresh_air_mode": {
                "keyword": "新风模式",
                "model_file": "./voices/models/fresh-air-climate.table",
                "callback_recognized": self.climate_bedroom.toggle_fresh_air_mode,
            },
            "toggle_health_mode": {
                "keyword": "健康模式",
                "model_file": "./voices/models/health-mode-climate.table",
                "callback_recognized": self.climate_bedroom.toggle_health_mode,
            },
            "toggle_quiet_mode": {
                "keyword": "静音模式",
                "model_file": "./voices/models/quiet-mode-climate.table",
                "callback_recognized": self.climate_bedroom.toggle_quiet_mode,
            },
            "response_no": {
                "keyword": "不用了",
                "model_file": "./voices/models/response-no.table",
                "callback_recognized": lambda: self.callback_to_response_no(),
            },
            "response_yes": {
                "keyword": "好的",
                "model_file": "./voices/models/response-yes.table",
                "callback_recognized": lambda: self.callback_to_response_yes(),
            },
        }
        self._keyword_recognizers_setup()

    def set_response_value(self, val):
        self.response_user = val

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
                AI_Server.response_time_counter = AI_Server.response_timeout
                callback()
                # to recognize keyword again.
                recognizer.recognize_once_async(keyword_model)

        return recognized_keyword_cb

    def auto_cool_mode(
        self,
        temperature: int = 26,
        total_simples=30,
    ):
        self.climate_bedroom.fast_cool_mode(temperature=temperature)
        self.light_bedroom.adjust_fan_speed_to_max()

        async def auto_cool_mode_monitor():
            await asyncio.sleep(1)
            result = await self.ws_client_esp32.get_statistc_temp_hum(total_simples)
            self.speaker.speak_text(
                "已全速启动空调和吊扇，目标温度为{:.1f}摄氏度。".format(temperature)
            )
            if result:
                self.speaker.speak_text(
                    "当前室内温度{:.1f}摄氏度，空气湿度{:.1f}%。".format(
                        result["temperature"]["mean"], result["humidity"]["mean"]
                    )
                )
            await asyncio.sleep(300)
            while True:
                result = await self.ws_client_esp32.get_statistc_temp_hum(total_simples)
                if not result:
                    await asyncio.sleep(10)
                else:
                    print(result)
                    temp_stdev = result["temperature"]["stdev"]
                    # if temp_stdev < 0.1:
                    if temp_stdev < 0.05:
                        await asyncio.sleep(15)
                        self.speaker.play_receive_response()
                        self.speaker.speak_text(
                            "当前室内温度稳定在{:.1f}摄氏度，空气湿度{:.1f}%。空调将进入健康和静音模式，吊扇速度降至最低。".format(
                                result["temperature"]["mean"],
                                result["humidity"]["mean"],
                            )
                        )
                        await asyncio.sleep(1)
                        self.climate_bedroom.turn_on_health_mode()
                        self.climate_bedroom.turn_on_quiet_mode()
                        self.light_bedroom.adjust_fan_speed_to_min()
                        break
                await asyncio.sleep(30)

        def run_async_play():
            asyncio.run(auto_cool_mode_monitor())

        thread = threading.Thread(target=run_async_play)
        thread.daemon = True
        thread.start()
        return thread

    async def monitor_tem_hum(self):
        total_simples = 30
        await asyncio.sleep(300)

        def callback_for_yes():
            self.auto_cool_mode()
            self.callback_to_response_yes = None

        def callback_for_no():
            AI_Server.response_time_counter = 0
            self.callback_to_response_no = None

        while True:
            result = await self.ws_client_esp32.get_statistc_temp_hum(total_simples)
            if result:
                tem = result["temperature"]["mean"]
                hum = result["humidity"]["mean"]
                if tem >= 31 or (tem >= 29 and hum >= 60):
                    self.speaker.play_receive_response()
                    self.speaker.speak_text(
                        "当前室内温度{:.1f}摄氏度，空气湿度{:.1f}%。需要启动空调吗？".format(
                            tem,
                            hum,
                        )
                    )
                    self.callback_to_response_yes = callback_for_yes
                    self.callback_to_response_no = callback_for_no
                    self.activate_response_keyword_recogizers()
                    break ##############################
            await asyncio.sleep(60)

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
            self.stop_keyword_recogizers(),
            # self.monitor_tem_hum(),
            self.ws_client_esp32.sample_tem_hum(),
            self.ws_client_esp32.receive_messages(),  # WebSocket消息接收任务
            self.ws_client_esp32.heartbeat_task(),  # 心跳任务
            # loop.run_in_executor(executor, self.sync_task, stop_event),  # 同步任务
        ]

        # 运行所有任务，直到其中一个完成或被取消
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("程序被用户中断")
        finally:
            # 清理资源
            await self.ws_client_esp32.close()
            self._close_porcupine()
            stop_event.set()
            executor.shutdown()


AI = AI_Server(configure_path="./configure.json")

if __name__ == "__main__":
    # 启动主事件循环
    asyncio.run(AI.main())
