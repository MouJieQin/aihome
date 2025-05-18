import asyncio
import websockets
import datetime
import json
from typing import *

# WebSocket客户端类 - 处理WebSocket连接和消息收发
class Websocket_client_esp32:
    def __init__(self, uri):
        self.uri = uri
        self.websocket = None
        self.resp_stack = {}

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
        if not self.websocket:
            print("WebSocket未连接")
            return
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
        except Exception as e:
            print(f"接收消息时出错: {e}")
        finally:
            await self.close()

    async def close(self):
        if self.websocket:
            await self.websocket.close()

    @staticmethod
    def get_now_timestamp() -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

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
                        return {
                            "temperature": mess["temperature"],
                            "humidity": mess["humidity"],
                        }
            await asyncio.sleep(poll_interval)
            counter += poll_interval
        return None

    # 异步任务示例 - 定期执行的心跳任务
    async def heartbeat_task(self, interval=5):
        """定期向WebSocket服务器发送心跳消息"""
        message = {"message": "heartbeat"}
        heartbeat_mess = json.dumps(message, ensure_ascii=False)
        while True:
            await self.send_message(heartbeat_mess)
            await asyncio.sleep(interval)
