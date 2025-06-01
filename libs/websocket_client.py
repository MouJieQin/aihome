import asyncio
import websockets
import datetime
import json
import math
from libs.log_config import logger
from typing import Dict, Any, Optional


class MathUtils:
    """
    A utility class for mathematical operations.
    """

    @staticmethod
    def mean(data):
        """
        Calculate the mean of a list of numbers.

        Args:
            data (list): A list of numbers.

        Returns:
            float: The mean of the data.
        """
        n = len(data)
        mean = sum(data) / n
        return mean

    @staticmethod
    def variance(data):
        """
        Calculate the variance of a list of numbers.

        Args:
            data (list): A list of numbers.

        Returns:
            float: The variance of the data.
        """
        mean = MathUtils.mean(data)
        n = len(data)
        deviations = [(x - mean) ** 2 for x in data]
        variance = sum(deviations) / n
        return variance

    @staticmethod
    def stdev(data):
        """
        Calculate the standard deviation of a list of numbers.

        Args:
            data (list): A list of numbers.

        Returns:
            float: The standard deviation of the data.
        """
        return math.sqrt(MathUtils.variance(data))


class Websocket_client_esp32:
    """
    WebSocket client class - handles WebSocket connections and message sending/receiving.
    """

    def __init__(self, uri):
        self.uri = uri
        self.websocket = None
        self.resp_stack = {}
        self.record = {}
        self.print_exception_flag = False

    async def connect(self) -> bool:
        """
        Establish a WebSocket connection.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        try:
            self.websocket = await websockets.connect(self.uri)
            logger.info(f"WebSocket connection established: {self.uri}")
            self.print_exception_flag = False
            return True
        except Exception as e:
            if self.print_exception_flag:
                logger.exception(f"WebSocket connection failed.")
            else:
                self.print_exception_flag = True
                logger.exception(f"WebSocket connection failed: {e}")
            return False

    async def _send_message(self, message) -> bool:
        """
        Send a message to the server.

        Args:
            message (str): The message to send.

        Returns:
            bool: True if the message is sent successfully, False otherwise.
        """
        if self.websocket:
            try:
                await self.websocket.send(message)
                logger.debug(f"Sent message: {message}")
                return True
            except Exception as e:
                logger.exception(f"Failed to send message: {e}")
                return False
        return False

    async def receive_messages(self):
        """
        Continuously receive messages from the server.
        """
        while True:
            if not self.websocket:
                logger.error("WebSocket is not connected")
            else:
                try:
                    async for message in self.websocket:
                        logger.debug(f"Received message: {message}")
                        try:
                            mess = json.loads(message)
                            self.resp_stack[mess["id"]] = mess
                        except json.JSONDecodeError:
                            logger.exception(f"Failed to parse message: {message}")
                except websockets.exceptions.ConnectionClosedOK:
                    logger.info("WebSocket connection closed normally")
                except websockets.exceptions.ConnectionClosedError as e:
                    logger.exception(f"WebSocket connection closed unexpectedly: {e}")
                    self.websocket = None
                except Exception as e:
                    logger.exception(f"Error receiving message: {e}")
                finally:
                    await self.close()
            await asyncio.sleep(3)

    async def close(self):
        """
        Close the WebSocket connection.
        """
        if self.websocket:
            await self.websocket.close()

    @staticmethod
    def _get_now_timestamp() -> str:
        """
        Get the current timestamp in a specific format.

        Returns:
            str: The current timestamp.
        """
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    async def _get_sensor_data(
        self, message_type: str, timeout: float = 3, poll_interval: float = 0.1
    ) -> Optional[Dict]:
        """
        Get sensor data from the server.

        Args:
            message_type (str): The type of sensor data to request.
            timeout (float, optional): The timeout duration in seconds. Defaults to 3.
            poll_interval (float, optional): The polling interval in seconds. Defaults to 0.1.

        Returns:
            Optional[Dict]: The sensor data if available, None otherwise.
        """
        message = {
            "from": "AI_server",
            "id": self._get_now_timestamp(),
            "to": "esp32_sensors",
            "type": message_type,
        }
        txt_message = json.dumps(message, ensure_ascii=False)
        if not await self._send_message(txt_message):
            return None
        counter: float = 0
        while counter < timeout:
            if message["id"] in self.resp_stack.keys():
                mess = self.resp_stack.pop(message["id"])
                if mess["from"] == "esp32_sensors" and mess["type"] == message_type:
                    if message_type == "ch2o" and mess["success"]:
                        return {
                            "timestamp": message["id"],
                            "ppb": mess["ppb"],
                            "mgm3": mess["mgm3"],
                        }
                    elif message_type == "humidity_temperature" and mess["temperature"]:
                        return {
                            "timestamp": message["id"],
                            "temperature": mess["temperature"],
                            "humidity": mess["humidity"],
                        }
            await asyncio.sleep(poll_interval)
            counter += poll_interval
        return None

    async def get_ch2o(
        self, timeout: float = 3, poll_interval: float = 0.1
    ) -> Optional[Dict]:
        """
        Get CH2O sensor data from the server.

        Args:
            timeout (float, optional): The timeout duration in seconds. Defaults to 3.
            poll_interval (float, optional): The polling interval in seconds. Defaults to 0.1.

        Returns:
            Optional[Dict]: The CH2O sensor data if available, None otherwise.
        """
        return await self._get_sensor_data("ch2o", timeout, poll_interval)

    async def get_temperature_humidity(
        self, timeout: float = 5, poll_interval: float = 0.1
    ) -> Optional[Dict]:
        """
        Get temperature and humidity sensor data from the server.

        Args:
            timeout (float, optional): The timeout duration in seconds. Defaults to 5.
            poll_interval (float, optional): The polling interval in seconds. Defaults to 0.1.

        Returns:
            Optional[Dict]: The temperature and humidity sensor data if available, None otherwise.
        """
        return await self._get_sensor_data(
            "humidity_temperature", timeout, poll_interval
        )

    async def get_statistc_temp_hum(self, total_simples: int = 10) -> Optional[Dict]:
        """
        Get statistical data for temperature and humidity.

        Args:
            total_simples (int, optional): The number of samples to consider. Defaults to 10.

        Returns:
            Optional[Dict]: The statistical data for temperature and humidity if available, None otherwise.
        """
        samples_tem = self.record["temperature"][-total_simples:]
        samples_hum = self.record["humidity"][-total_simples:]
        if not samples_tem:
            return None
        else:
            return {
                "temperature": {
                    "mean": MathUtils.mean(samples_tem),
                    "stdev": MathUtils.stdev(samples_tem),
                },
                "humidity": {
                    "mean": MathUtils.mean(samples_hum),
                    "stdev": MathUtils.stdev(samples_hum),
                },
            }

    async def sample_tem_hum(self, sample_interval: int = 10):
        """
        Continuously sample temperature and humidity data.

        Args:
            sample_interval (int, optional): The sampling interval in seconds. Defaults to 10.
        """
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

    async def heartbeat_task(self, interval=5):
        """
        Periodically send a heartbeat message to the WebSocket server.

        Args:
            interval (int, optional): The interval in seconds between heartbeat messages. Defaults to 5.
        """
        message = {"message": "heartbeat"}
        heartbeat_mess = json.dumps(message, ensure_ascii=False)
        while True:
            if not await self._send_message(heartbeat_mess):
                while not await self.connect():
                    await asyncio.sleep(interval)
            await asyncio.sleep(interval)
