import asyncio
import websockets
import datetime
import json
import math
from typing import *


# WebSocket客户端类 - 处理WebSocket连接和消息收发
class Websocket_client_esp32:
    @staticmethod
    def mean(data):
        n = len(data)
        mean = sum(data) / n
        return mean

    @staticmethod
    def variance(data):
        mean = Websocket_client_esp32.mean(data)
        n = len(data)
        deviations = [(x - mean) ** 2 for x in data]
        variance = sum(deviations) / n
        return variance

    @staticmethod
    def stdev(data):
        return math.sqrt(Websocket_client_esp32.variance(data))

    def __init__(self, uri):
        self.uri = uri
        self.websocket = None
        self.resp_stack = {}
        self.record = {}

    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            self.websocket = await websockets.connect(self.uri)
            print(f"WebSocket连接已建立: {self.uri}")
            return True
        except Exception as e:
            print(f"WebSocket连接失败: {e}")
            return False

    async def send_message(self, message) -> bool:
        """向服务器发送消息"""
        if self.websocket:
            try:
                await self.websocket.send(message)
                print(f"发送消息: {message}")
                return True
            except Exception as e:
                print(f"发送消息失败: {e}")
                return False
        return False

    async def receive_messages(self):
        """持续接收服务器消息"""
        while True:
            if not self.websocket:
                print("WebSocket未连接")
            else:
                try:
                    # while True:
                    # message = await self.websocket.recv()
                    async for message in self.websocket:
                        print(f"收到消息: {message}")
                        try:
                            mess = json.loads(message)
                            self.resp_stack[mess["id"]] = mess
                        except json.JSONDecodeError:
                            print(f"消息解析失败: {message}")
                except websockets.exceptions.ConnectionClosedOK:
                    print("WebSocket连接已正常关闭")
                except websockets.exceptions.ConnectionClosedError as e:
                    print(f"WebSocket连接意外关闭: {e}")
                    self.websocket = None
                except Exception as e:
                    print(f"接收消息时出错: {e}")
                finally:
                    await self.close()
            await asyncio.sleep(3)

    async def close(self):
        if self.websocket:
            await self.websocket.close()

    @staticmethod
    def get_now_timestamp() -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    async def get_ch2o(self, timeout: float = 3, poll_interval: float = 0.1) -> Dict:
        message = {}
        message["from"] = "AI_server"
        id_timestamp = Websocket_client_esp32.get_now_timestamp()
        message["id"] = id_timestamp
        message["to"] = "esp32_sensors"
        message["type"] = "ch2o"
        txt_message = json.dumps(message, ensure_ascii=False)
        if not await self.send_message(txt_message):
            return None
        counter: float = 0
        while counter < timeout:
            if id_timestamp in self.resp_stack.keys():
                mess = self.resp_stack.pop(id_timestamp)
                if mess["from"] == "esp32_sensors":
                    if mess["type"] == "ch2o":
                        if mess["success"]:
                            return {
                                "timestamp": id_timestamp,
                                "ppb": mess["ppb"],
                                "mgm3": mess["mgm3"],
                            }
            await asyncio.sleep(poll_interval)
            counter += poll_interval
        return None

    async def get_temperature_humidity(
        self, timeout: float = 5, poll_interval: float = 0.1
    ) -> Dict:
        message = {}
        message["from"] = "AI_server"
        id_timestamp = Websocket_client_esp32.get_now_timestamp()
        message["id"] = id_timestamp
        message["to"] = "esp32_sensors"
        message["type"] = "humidity_temperature"
        txt_message = json.dumps(message, ensure_ascii=False)
        if not await self.send_message(txt_message):
            return None
        counter: float = 0
        while counter < timeout:
            if id_timestamp in self.resp_stack.keys():
                mess = self.resp_stack.pop(id_timestamp)
                if mess["from"] == "esp32_sensors":
                    if mess["type"] == "humidity_temperature":
                        if mess["temperature"]:
                            return {
                                "timestamp": id_timestamp,
                                "temperature": mess["temperature"],
                                "humidity": mess["humidity"],
                            }
            await asyncio.sleep(poll_interval)
            counter += poll_interval
        return None

    async def sample_tem_hum(self, sample_interval: int = 10):
        self.record["timestamp"] = []
        self.record["temperature"] = []
        self.record["humidity"] = []
        while True:
            result = await self.get_temperature_humidity()
            if result:
                if len(self.record["timestamp"]) >= 200:
                    self.record["timestamp"] = self.record["timestamp"][-100:]
                    self.record["temperature"] = self.record["temperature"][-100:]
                    self.record["humidity"] = self.record["humidity"][-100:]
                self.record["timestamp"].append(result["timestamp"])
                self.record["temperature"].append(result["temperature"])
                self.record["humidity"].append(result["humidity"])
            await asyncio.sleep(sample_interval)

    async def get_statistc_temp_hum(self, total_simples: int = 10) -> Dict:
        samples_tem = self.record["temperature"][-total_simples:]
        samples_hum = self.record["humidity"][-total_simples:]
        if not samples_tem:
            return None
        else:
            return {
                "temperature": {
                    "mean": Websocket_client_esp32.mean(samples_tem),
                    "stdev": Websocket_client_esp32.stdev(samples_tem),
                },
                "humidity": {
                    "mean": Websocket_client_esp32.mean(samples_hum),
                    "stdev": Websocket_client_esp32.stdev(samples_hum),
                },
            }

    # 异步任务示例 - 定期执行的心跳任务
    async def heartbeat_task(self, interval=5):
        """定期向WebSocket服务器发送心跳消息"""
        message = {"message": "heartbeat"}
        heartbeat_mess = json.dumps(message, ensure_ascii=False)
        while True:
            if not await self.send_message(heartbeat_mess):
                while not await self.connect():
                    await asyncio.sleep(interval)
            await asyncio.sleep(interval)
