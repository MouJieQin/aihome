from libs.bedroom_light import LightBedroom
from libs.bedroom_climate import ClimateBedroom
from libs.elec_meter_controller import ElecMeterController
from libs.homeassistant_sensors import HomeAssistantSensors
from libs.websocket_client import Websocket_client_esp32
from libs.speaker import Speaker
from libs.recognizer import Recognizer
from libs.homeassistant_vm_manager import VirtualBoxController
from libs.task_scheduler import TaskScheduler
from libs.porcupine_manager import PorcupineManager
from libs.log_config import logger
import azure.cognitiveservices.speech as speechsdk
import asyncio
import json
import datetime
import threading
from typing import Dict, Optional, Tuple, Any, Callable


class AIserverDevices:
    """
    This class is a placeholder for AI server devices.
    It currently does not contain any functionality or attributes.
    """

    RESPONSE_TIMEOUT = 10
    RESPONSE_INTERVAL = 1

    class DateTimeEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, datetime):
                return o.isoformat()
            try:
                return super().default(o)
            except TypeError:
                return str(o)

    def __init__(self, configure: dict):
        """
        Initialize the AI server devices with the provided configuration.
        :param configure: A dictionary containing configuration settings for the devices.
        """
        self.configure = configure
        self.callback_to_response_yes: Optional[Callable] = None
        self.callback_to_response_no: Optional[Callable] = None
        self._init_vm_manager()
        self._init_devices()
        self._init_porcupine_manager()
        self._init_task_scheduler()
        self._init_keyword_recognizers()

    def _init_vm_manager(self):
        """Initialize the VirtualBox manager and start the VM."""
        self.ha_vm_manager = VirtualBoxController(self.configure)
        self.ha_vm_manager.start_vm()

    def _init_devices(self):
        """Initialize all smart devices."""
        self.speaker = Speaker(self.configure)
        self.light_bedroom = LightBedroom(self.configure)
        self.climate_bedroom = ClimateBedroom(self.configure)
        self.elec_controller = ElecMeterController(self.configure)
        self.sensors = HomeAssistantSensors(self.configure)
        self.esp32_config = self.configure["esp32"]
        self.esp32_bedroom_config = self.esp32_config["bedroom"]
        self.ws_client_esp32 = Websocket_client_esp32(self.esp32_bedroom_config["uri"])
        self.recognizer = Recognizer(self.configure, self._recognized_callback)
        self._pause_ch2o_monitor_seconds = 0
        self._json_states_of_all_devices = "{}"

    async def response_timer_demon(self):
        """Stop non-keep-alive keyword recognizers after timeout."""
        while True:
            if self._response_time_counter > 0:
                while self._response_time_counter > 0:
                    self._response_time_counter -= self.RESPONSE_INTERVAL
                    logger.debug(
                        "AIserver.response_time_counter:",
                        self._response_time_counter,
                    )
                    await asyncio.sleep(self.RESPONSE_INTERVAL)
                self.stop_keyword_recognizers()
                self.recognizer.stop_recognizer()
                self.speaker.play_end_record()
                self.porcupine_manager.set_awake(False)
            await asyncio.sleep(self.RESPONSE_INTERVAL)

    @property
    def _response_time_counter(self):
        return getattr(self.__class__, "response_time_counter", 0)

    @_response_time_counter.setter
    def _response_time_counter(self, value):
        setattr(self.__class__, "response_time_counter", value)

    def _reset_response_time_counter(self, val: int = RESPONSE_TIMEOUT):
        self._response_time_counter = val

    def _awake_callback(self):
        if not self.porcupine_manager.is_awaked():
            self.activate_keyword_recognizers()
            self.acquire_json_states_of_all_devices_async()
        else:
            self._reset_response_time_counter()
            self.speaker.play_start_record()
        self.speaker.stop_playback()

    def _enter_silent_mode(self):
        """Enter silent mode where wake words are disabled."""
        self.recognizer.stop_recognizer_sync()
        self.speaker.play_receive_response()
        logger.info("Enter silent mode.")
        self.speaker.speak_text("已启动静默，唤醒词被禁用。")
        self.stop_keyword_recognizers()
        self.porcupine_manager.start_recognize_silent_mode_off()

    def _exit_silent_mode(self):
        """Exit silent mode where wake words are enabled again."""
        self.speaker.play_receive_response()
        logger.info("Exit silent mode.")
        self.speaker.speak_text("已结束静默，唤醒词已启用。")

    def _init_porcupine_manager(self):
        """Initialize the Porcupine manager for wake word detection."""
        self.porcupine_manager = PorcupineManager(
            self.configure,
            self._awake_callback,
            self._enter_silent_mode,
            self._exit_silent_mode,
        )

    def _recognized_callback(self, cur_recognized_text: str):
        """Callback function for recognized words."""
        raise NotImplementedError(
            "This method should be implemented in subclasses to handle recognized text."
        )

    def _ai_assistant_response_callback(self, commands: Dict):
        """Callback function for AI assistant response."""
        raise NotImplementedError(
            "This method should be implemented in subclasses to handle AI assistant responses."
        )

    def _task_scheduler_callback(self, args: Dict):
        """Callback function for task scheduler."""
        self.speaker.play_receive_response()
        self._ai_assistant_response_callback(args)

    def _init_task_scheduler(self):
        """Initialize the TaskScheduler."""
        self.task_scheduler = TaskScheduler(
            self.configure, self._task_scheduler_callback
        )
        self.task_scheduler.start()

    def _add_scheduler_task(
        self,
        task_name: str,
        run_at: str,
        interval: Optional[Tuple[int, int, int, int]] = None,
        args: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add a task to the scheduler."""
        return self.task_scheduler.add_task(task_name, run_at, interval, args)

    def _init_keyword_recognizers(self):
        """Initialize keyword recognizers."""
        self.response_keyword_list = [
            "response_no",
            "response_yes",
        ]
        self.independent_keyword_list = [
            *self.response_keyword_list,
        ]
        self.keyword_recognizers = self._create_keyword_recognizers()
        self._setup_keyword_recognizers()

    def _create_keyword_recognizers(self) -> Dict:
        """Create keyword recognizers configuration."""
        return {
            "turn_on_light": {
                "keyword": "开灯",
                "model_file": "./voices/models/turn-on-light.table",
                "model": None,
                "recognizer": None,
                "recognized_keyword_cb": None,
                "canceled_keyword_cb": None,
                "callback_recognized": lambda: self.light_bedroom.set_light_mode(
                    "Reception Mode"
                ),
            },
            "turn_off_light": {
                "keyword": "关灯",
                "model_file": "./voices/models/turn-off-light.table",
                "callback_recognized": self.light_bedroom.turn_off_light,
            },
            "turn_off_fan": {
                "keyword": "关闭风扇",
                "model_file": "./voices/models/turn-off-fan.table",
                "callback_recognized": self.light_bedroom.turn_off_fan,
            },
            "response_no": {
                "keyword": "不用了",
                "model_file": "./voices/models/response-no.table",
                "callback_recognized": lambda: self._call_callback(
                    self.callback_to_response_no
                ),
            },
            "response_yes": {
                "keyword": "好的",
                "model_file": "./voices/models/response-yes.table",
                "callback_recognized": lambda: self._call_callback(
                    self.callback_to_response_yes
                ),
            },
        }

    def _call_callback(self, callback: Optional[Callable]):
        """Call the callback function if it's not None."""
        if callback:
            callback()

    def _setup_keyword_recognizer(self, keyword: str):
        """Set up keyword recognizers with models and callbacks."""
        items = self.keyword_recognizers[keyword]
        items["model"] = speechsdk.KeywordRecognitionModel(items["model_file"])
        items["recognizer"] = speechsdk.KeywordRecognizer()
        items["recognized_keyword_cb"] = self._recognized_keyword_cb(
            items["keyword"],
            items["recognizer"],
            items["model"],
            items["callback_recognized"],
        )
        items["recognizer"].recognized.connect(items["recognized_keyword_cb"])
        items["canceled_keyword_cb"] = self._canceled_keyword_cb(items["keyword"])
        items["recognizer"].canceled.connect(items["canceled_keyword_cb"])

    def _setup_keyword_recognizers(self):
        """Set up keyword recognizers with models and callbacks."""
        for key in self.keyword_recognizers.keys():
            self._setup_keyword_recognizer(key)

    def activate_keyword_recognizers(self):
        """Activate all keyword recognizers except keep-alive ones."""
        self.speaker.play_start_record()
        self.recognizer.stop_recognizer_sync()
        self.recognizer.start_recognizer()
        self.porcupine_manager.start_recognize_silent_mode_on()
        for key, items in self.keyword_recognizers.items():
            if key not in self.independent_keyword_list:
                items["recognizer"].recognize_once_async(items["model"])
        self._reset_response_time_counter()
        self.porcupine_manager.set_awake(True)

    def activate_keyword_recognizer(self, keyword: str):
        """Activate a specific keyword recognizer."""
        if keyword in self.keyword_recognizers:
            items = self.keyword_recognizers[keyword]
            items["recognizer"].recognize_once_async(items["model"])
            logger.info(f"Activated keyword recognizer for '{keyword}'.")
        else:
            logger.warning(f"Keyword recognizer for '{keyword}' not found.")

    def activate_response_keyword_recognizers(self):
        """Activate response-related keyword recognizers."""
        for key in self.response_keyword_list:
            item = self.keyword_recognizers[key]
            item["recognizer"].recognize_once_async(item["model"])
        self._reset_response_time_counter()
        self.speaker.play_start_record()

    def stop_keyword_recognizers(self):
        """Stop keyword recognizers."""
        if not self.porcupine_manager.is_in_silent_mode():
            self.porcupine_manager.stop_recognize_silent_mode_on()
        for key, items in self.keyword_recognizers.items():
            if key not in self.independent_keyword_list:
                items["recognizer"].stop_recognition_async().get()

    def stop_keyword_recognizer(self, keyword: str):
        """Stop specific keyword recognizers or all."""
        if keyword in self.keyword_recognizers:
            self.keyword_recognizers[keyword][
                "recognizer"
            ].stop_recognition_async().get()
        else:
            logger.warning(f"Keyword recognizer for '{keyword}' not found.")

    @staticmethod
    def _canceled_keyword_cb(keyword: str) -> Callable:
        """Create a callback for canceled keyword recognition."""

        def canceled_keyword_cb(evt):
            result = evt.result
            if result.reason == speechsdk.ResultReason.Canceled:
                logger.info(f"{keyword} CANCELED: {result.cancellation_details.reason}")
            else:
                logger.error(f"{keyword} CANCELED: {result.reason} - {result.text}")

        return canceled_keyword_cb

    def _recognized_keyword_cb(
        self,
        keyword: str,
        recognizer: speechsdk.KeywordRecognizer,
        keyword_model: speechsdk.KeywordRecognitionModel,
        callback: Callable,
    ) -> Callable:
        """Create a callback for recognized keyword."""

        def recognized_keyword_cb(self: AIserverDevices, evt):
            try:
                result = evt.result
                if result.reason == speechsdk.ResultReason.RecognizedKeyword:
                    # Avoid keywords being recognized in real-time recognition
                    if len(keyword) < self.recognizer.get_max_len_recogized_words():
                        return
                    self.recognizer.stop_recognizer()
                    self_ = AIserverDevices.__new__(AIserverDevices)
                    self_._reset_response_time_counter(0)
                    callback()
                    # if keyword not in self.independent_keyword_list:
                    #     recognizer.recognize_once_async(keyword_model)
                else:
                    logger.error(
                        f"{keyword} RECOGNIZED: {result.reason} - {result.text}"
                    )
            except Exception as e:
                logger.error(f"Error in recognized keyword callback: {e}")

        return lambda evt: recognized_keyword_cb(self, evt)

    def acquire_json_states_of_all_devices_async(self):
        """Get states of all devices."""

        self._json_states_of_all_devices = "{}"

        def set_json_states_of_all_devices():
            try:
                self._json_states_of_all_devices = self.get_json_states_of_all_devices()
            except Exception as e:
                logger.error(f"Error in acquiring json states of all devices: {e}")
                self._json_states_of_all_devices = "{}"

        threading.Thread(target=set_json_states_of_all_devices, daemon=True).start()

    def get_json_states_of_all_devices(self) -> str:
        """Get states of all devices."""
        return json.dumps(
            self.get_states_of_all_devices(),
            ensure_ascii=False,
            cls=self.DateTimeEncoder,
        )

    def get_states_of_all_devices(self) -> Dict:
        """Get states of all devices."""
        return {
            "light_bedroom": self.light_bedroom.get_states(),
            "climate_bedroom": self.climate_bedroom.get_states(),
            "elec_controller": self.elec_controller.get_states(),
            "sensors": self.sensors.get_states(),
        }

    def auto_cool_mode(
        self,
        temperature: int = 26,
        total_sample: int = 30,
    ) -> threading.Thread:
        """Start the auto cool mode and monitor the temperature and humidity."""
        self.climate_bedroom.fast_cool_mode(temperature=temperature)
        self.light_bedroom.adjust_fan_speed_to_max()

        async def auto_cool_mode_monitor():
            await asyncio.sleep(1)
            result = await self.ws_client_esp32.get_statistc_temp_hum(total_sample)
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
                result = await self.ws_client_esp32.get_statistc_temp_hum(total_sample)
                if not result:
                    await asyncio.sleep(10)
                else:
                    temp_stdev = result["temperature"]["stdev"]
                    if temp_stdev < 0.07:
                        await asyncio.sleep(15)
                        self.speaker.play_receive_response()
                        self.speaker.speak_text(
                            "当前室内温度稳定在{:.1f}摄氏度，空气湿度{:.1f}%。空调将进入健康和静音模式，吊扇速度降至最低。".format(
                                result["temperature"]["mean"],
                                result["humidity"]["mean"],
                            )
                        )
                        await asyncio.sleep(1)
                        self.climate_bedroom.default_cool_mode()
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
        """Monitor the temperature and humidity and prompt user if necessary."""
        total_sample = 30
        await asyncio.sleep(300)

        def callback_for_yes():
            self.auto_cool_mode()
            self.callback_to_response_yes = None

        def callback_for_no():
            self._response_time_counter = 0
            self.callback_to_response_no = None

        while True:
            result = await self.ws_client_esp32.get_statistc_temp_hum(total_sample)
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
                    self.activate_response_keyword_recognizers()
                    break
            await asyncio.sleep(60)

    async def monitor_ch2o(self):
        """Monitor the formaldehyde concentration and prompt user if necessary."""
        while True:
            result = await self.ws_client_esp32.get_ch2o()
            if result:
                print("CH2O: {} ppb    {} mg/m3".format(result["ppb"], result["mgm3"]))
                if result["mgm3"] > 0.08:
                    self.speaker.play_receive_response()
                    self.speaker.speak_warning(
                        "警告！当前室内甲醛浓度为{}mg/m3，建议您开启门窗通风。".format(
                            result["mgm3"]
                        )
                    )
                    await asyncio.sleep(180)
                    await self._pause_ch2o_monitor()
            await asyncio.sleep(61)
            await self._pause_ch2o_monitor()

    async def _pause_ch2o_monitor(self):
        """Pause the CH2O monitor."""
        if self._pause_ch2o_monitor_seconds <= 0:
            return
        logger.info(f"CH2O监测已暂停，暂停时间为{self._pause_ch2o_monitor_seconds}秒")
        check_interval = 10.0  # 最大检查间隔为1秒
        while self._pause_ch2o_monitor_seconds > 0:
            await asyncio.sleep(check_interval)
            self._pause_ch2o_monitor_seconds -= check_interval
        logger.info("CH2O监测已恢复")

    def set_pause_ch2o_monitor_seconds(self, seconds: int):
        """Set the pause duration for CH2O monitoring."""
        self._pause_ch2o_monitor_seconds = seconds
        logger.info(f"设置CH2O监测暂停时间为{seconds}秒")
