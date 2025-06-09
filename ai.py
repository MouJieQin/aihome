import azure.cognitiveservices.speech as speechsdk
from concurrent.futures import ThreadPoolExecutor
import pvporcupine
import pyaudio
import struct
import asyncio
import json
import threading
import os
from typing import Dict, Callable, Optional
from libs.bedroom_light import LightBedroom
from libs.bedroom_climate import ClimateBedroom
from libs.elec_meter_controller import ElecMeterController
from libs.homeassistant_sensors import HomeAssistantSensors
from libs.websocket_client import Websocket_client_esp32
from libs.speaker import Speaker
from libs.recognizer import Recognizer
from libs.ai_assistant import AIassistant
from libs.homeassistant_vm_manager import VirtualBoxController
from libs.task_scheduler import TaskScheduler
from libs.log_config import logger
from datetime import datetime

os.chdir(os.path.dirname(__file__))


class AI_Server:
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

    def __init__(self, configure_path: str):
        self._load_configuration(configure_path)
        self._init_vm_manager()
        self._init_porcupine()
        self._init_devices()
        self._init_keyword_recognizers()
        self._init_ai_assistant()
        self._init_task_scheduler()

        self.response_user = None
        self.callback_to_response_yes: Optional[Callable] = None
        self.callback_to_response_no: Optional[Callable] = None

        self.is_activated = False

    def _load_configuration(self, configure_path: str):
        """Load configuration from the given file path."""
        with open(configure_path, mode="r", encoding="utf-8") as f:
            self.configure = json.load(f)

    def _init_vm_manager(self):
        """Initialize the VirtualBox manager and start the VM."""
        ha_vm_uuid = self.configure["virtualbox"]["ha_vm_uuid"]
        self.ha_vm_manager = VirtualBoxController(ha_vm_uuid)
        self.ha_vm_manager.start_vm()

    def _init_task_scheduler(self):
        """Initialize the TaskScheduler."""
        self.task_scheduler = TaskScheduler(self.configure)
        self.task_scheduler.start()

    def _init_ai_assistant(self):
        """Initialize the AI assistant."""
        self.supported_commands = self._create_supported_function()
        supported_commands_ = self._create_supported_function_for_ai_assistant()
        supported_commands_str = json.dumps(supported_commands_, ensure_ascii=False)
        self.ai_assistant = AIassistant(self.configure, supported_commands_str)

    def _init_porcupine(self):
        """Initialize Porcupine for wake word detection."""
        config_porcupine = self.configure["porcupine"]
        config_microphone = self.configure["microphone"]
        self.porcupine = pvporcupine.create(
            access_key=config_porcupine["access_key"],
            model_path=config_porcupine["model_path"],
            keyword_paths=[config_porcupine["keyword_paths"]],
        )
        self.pa = pyaudio.PyAudio()
        input_device_name = config_microphone["ai_assistant"]["input_device_name"]
        input_device_index = self._get_input_device_index_by_name(input_device_name)
        if input_device_index is None:
            logger.error(f"未找到名为 {input_device_name} 的输入设备")
            exit(1)
            return
        self.audio_stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            input_device_index=input_device_index,
            frames_per_buffer=self.porcupine.frame_length,
        )
        self._start_ai_awake_thread()

    def _get_input_device_index_by_name(self, device_name: str) -> Optional[int]:
        """Get the input device index by its name."""
        for i in range(self.pa.get_device_count()):
            device_info = self.pa.get_device_info_by_index(i)
            if (
                device_info["name"] == device_name
                and device_info["maxInputChannels"] != 0
            ):
                return i
        return None

    def _start_ai_awake_thread(self) -> threading.Thread:
        """Start the thread for wake word detection."""

        def run_ai_awake():
            """Run the wake word detection loop."""
            while True:
                if self.porcupine is None:
                    return
                pcm = self.audio_stream.read(
                    self.porcupine.frame_length, exception_on_overflow=False
                )
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                result = self.porcupine.process(pcm)
                if result >= 0:
                    logger.info(f"检测到唤醒词: あすな")
                    if not self.is_activated:
                        self.activate_keyword_recognizers()
                    else:
                        self._reset_response_time_counter()
                        self.speaker.play_start_record()

        thread = threading.Thread(target=run_ai_awake)
        thread.daemon = True
        thread.start()
        return thread

    def _close_porcupine(self):
        """Close Porcupine resources."""
        if self.pa is not None:
            self.pa.terminate()
        if self.audio_stream is not None:
            self.audio_stream.close()
        if self.porcupine is not None:
            self.porcupine.delete()

    def _init_devices(self):
        """Initialize all smart devices."""
        self.light_bedroom = LightBedroom(self.configure)
        self.climate_bedroom = ClimateBedroom(self.configure)
        self.elec_controller = ElecMeterController(self.configure)
        self.sensors = HomeAssistantSensors(self.configure)
        self.esp32_config = self.configure["esp32"]
        self.esp32_bedroom_config = self.esp32_config["bedroom"]
        self.ws_client_esp32 = Websocket_client_esp32(self.esp32_bedroom_config["uri"])
        self.speaker = Speaker(self.configure)
        self.recognizer = Recognizer(self.configure, self._recognized_callback)

    def _init_keyword_recognizers(self):
        """Initialize keyword recognizers."""
        self.independent_keyword_list = ["response_no", "response_yes"]
        self.keyword_recognizers = self._create_keyword_recognizers()
        self._setup_keyword_recognizers()

    def _recognized_callback(self, cur_recognized_text: str):
        """Callback function for recognized keywords."""
        self.recognizer.stop_recognizer()
        if len(cur_recognized_text) > 1:
            self.stop_keyword_recognizers()
            self._chat_with_ai_assistant(cur_recognized_text)

    def _chat_with_ai_assistant(self, user_input: str) -> Optional[str]:
        """Chat with AI assistant and return the response."""
        logger.info(f"User input: {user_input}")
        self.speaker.play_send_message()
        response = self.ai_assistant.chat(user_input, self.json_states_of_all_devices())
        logger.info(f"Assistant response: {response}")
        self.speaker.play_receive_response()
        if response:
            self._handle_ai_assistant_response(response)
        return response

    def _handle_ai_assistant_response(self, response: str):
        """Handle AI assistant response."""
        commands = json.loads(response)
        self.speaker.start_speaking_text(commands["あすな"])
        self._handle_ai_assistant_response_imple(commands, self.supported_commands)

    def _handle_ai_assistant_response_imple(self, commands: Dict, commands_: Dict):
        """Handle AI assistant response."""
        for key, items in commands.items():
            if key != "あすな":
                if "args" in items.keys():
                    commands_[key]["function"](**items["args"])
                else:
                    self._handle_ai_assistant_response_imple(items, commands_[key])

    def _create_supported_function_for_ai_assistant(self) -> Dict:
        """Create a dictionary of supported functions for AI assistant."""
        supported_functions = self._create_supported_function()
        self._create_supported_function_for_ai_assistant_imple(supported_functions)
        return supported_functions

    def _create_supported_function_for_ai_assistant_imple(
        self, supported_functions: Dict
    ):
        """Create a dictionary of supported functions for AI assistant."""
        for key, items in supported_functions.items():
            if "function" in items:
                supported_functions[key]["function"] = items["function"].__name__
            else:
                self._create_supported_function_for_ai_assistant_imple(items)

    def _create_supported_function(self) -> Dict:
        """Create a dictionary of supported functions."""
        return {
            "吊扇": {
                "风速": {
                    "function": self.light_bedroom.adjust_fan_speed_to_preset_value,
                    "args": {
                        "value": {
                            "type": "int",
                            "description": "[1, 22, 46, 70, 86, 100]分别对应一到六级风速百分比，当没说有特别说明时，风速指的是吊扇风速。",
                            "is_necessary": True,
                            "range": "[0,5]",
                            "condidates": {
                                0: {
                                    "name": "一级风速",
                                },
                                1: {
                                    "name": "二级风速",
                                },
                                2: {
                                    "name": "三级风速",
                                },
                                3: {
                                    "name": "四级风速",
                                },
                                4: {
                                    "name": "五级风速",
                                },
                                5: {
                                    "name": "六级风速",
                                },
                            },
                        }
                    },
                },
                "开关": {
                    "function": self.light_bedroom.switch_fan,
                    "args": {
                        "value": {
                            "type": "bool",
                            "is_necessary": True,
                            "condidates": {True: {"name": "开"}, False: {"name": "关"}},
                        }
                    },
                },
            },
            "灯光": {
                "模式": {
                    "function": self.light_bedroom.set_light_mode,
                    "args": {
                        "mode": {
                            "type": "str",
                            "is_necessary": True,
                            "condidates": {
                                "Cinema Mode": {"name": "影院模式"},
                                "Entertainment Mode": {"name": "娱乐模式"},
                                "Reception Mode": {"name": "会客模式"},
                                "Night Light": {"name": "夜灯模式"},
                            },
                        }
                    },
                },
                "亮度和色温": {
                    "function": self.light_bedroom.adjust_light_brightness_color_temp,
                    "args": {
                        "brightness": {
                            "type": "int",
                            "is_necessary": True,
                            "range": "[1,255]",
                        },
                        "color_temp_kelvin": {
                            "type": "int",
                            "is_necessary": True,
                            "range": "[2700,5700]",
                        },
                    },
                },
                "开关": {
                    "function": self.light_bedroom.switch_light,
                    "args": {
                        "value": {
                            "type": "bool",
                            "is_necessary": True,
                            "condidates": {True: {"name": "开"}, False: {"name": "关"}},
                        }
                    },
                },
            },
            "空调": {
                "预置模式": {
                    "function": self.climate_bedroom.set_preset_mode,
                    "args": {
                        "preset_mode": {
                            "type": "str",
                            "is_necessary": True,
                            "condidates": {
                                "eco": {"name": "节能"},
                                "boost": {"name": "强劲"},
                                "none": {"name": "无"},
                                "sleep": {"name": "睡眠"},
                                "away": {"name": "离家"},
                            },
                        }
                    },
                },
                "高级模式": {
                    "健康模式": {
                        "function": self.climate_bedroom.switch_health_mode,
                        "args": {
                            "value": {
                                "type": "bool",
                                "is_necessary": True,
                                "condidates": {
                                    True: {"name": "开"},
                                    False: {"name": "关"},
                                },
                            }
                        },
                    },
                    "新风模式": {
                        "function": self.climate_bedroom.switch_fresh_air_mode,
                        "args": {
                            "value": {
                                "type": "bool",
                                "is_necessary": True,
                                "condidates": {
                                    True: {"name": "开"},
                                    False: {"name": "关"},
                                },
                            }
                        },
                    },
                    "静音模式": {
                        "function": self.climate_bedroom.switch_quiet_mode,
                        "args": {
                            "value": {
                                "type": "bool",
                                "is_necessary": True,
                                "condidates": {
                                    True: {"name": "开"},
                                    False: {"name": "关"},
                                },
                            },
                        },
                    },
                },
                "面板灯光": {
                    "function": self.climate_bedroom.switch_panel_light,
                    "args": {
                        "value": {
                            "type": "bool",
                            "is_necessary": True,
                            "condidates": {
                                True: {"name": "开"},
                                False: {"name": "关"},
                            },
                        },
                    },
                },
                "开关": {
                    "function": self.climate_bedroom.switch_climate,
                    "args": {
                        "value": {
                            "type": "bool",
                            "is_necessary": True,
                            "condidates": {
                                True: {"name": "开"},
                                False: {"name": "关"},
                            },
                        }
                    },
                },
                "自定义模式": {
                    "制冷": {
                        "function": self.auto_cool_mode,
                        "description": "先全速制冷，通过室内温度的标准差判断温度稳定后自动进入健康模式和静音模式。",
                        "args": {
                            "temperature": {
                                "type": "int",
                                "description": "目标温度，单位为摄氏度",
                                "is_necessary": False,
                                "default": 25,
                                "range": "[8,30]",
                            },
                            "total_sample": {
                                "type": "int",
                                "is_necessary": False,
                            },
                        },
                    }
                },
                "风速": {
                    "function": self.climate_bedroom.set_fan_mode,
                    "args": {
                        "fan_mode": {
                            "type": "str",
                            "is_necessary": True,
                            "condidates": {
                                "low": {"name": "低速"},
                                "medium low": {"name": "中低速"},
                                "medium": {"name": "中速"},
                                "medium high": {"name": "中高速"},
                                "high": {"name": "高速"},
                                "auto": {"name": "自动"},
                            },
                        }
                    },
                },
                "扫风": {
                    "function": self.climate_bedroom.set_swing_mode,
                    "args": {
                        "swing_mode": {
                            "type": "str",
                            "is_necessary": True,
                            "condidates": {
                                "vertical": {"name": "上下扫风"},
                                "horizontal": {"name": "左右扫风"},
                                "both": {"name": "上下左右扫风"},
                                "off": {"name": "关闭扫风"},
                            },
                        }
                    },
                },
                "温度设置": {
                    "function": self.climate_bedroom.set_temperature,
                    "args": {
                        "temperature": {
                            "type": "int",
                            "is_necessary": True,
                            "range": "[8,30]",
                        }
                    },
                },
            },
            "插座": {
                "开关": {
                    "function": self.elec_controller.switch_controller,
                    "description": "目前控制电蚊香的开关",
                    "args": {
                        "value": {
                            "type": "bool",
                            "is_necessary": True,
                            "condidates": {
                                True: {"name": "开"},
                                False: {"name": "关"},
                            },
                        }
                    },
                }
            },
            "其它": {
                "function": self._handle_others,
                "args": {
                    "type": {
                        "type": "str",
                        "is_necessary": True,
                        "condidates": {
                            "query": {
                                "name": "查询家电的状态，直接在「あすな」的回复中给出查询结果"
                            },
                            "unsupported": {"name": "不支持该指令"},
                            "confused": {"name": "无法识别指令"},
                            "others": {
                                "name": "其它指令",
                                "description": "其它与家电无关但可以做到的指令。",
                            },
                        },
                    }
                },
            },
        }

    def _handle_others(self, type: str):
        """Handle errors based on the error type."""
        if type == "unsupported":
            self._handle_unsupported_function()
        elif type == "confused":
            self._handle_confused_function()
        elif type == "query":
            self._handle_query_function()

    def _handle_query_function(self):
        """Handle query functions."""
        logger.info("查询家电的状态")

    def _handle_unsupported_function(self):
        """Handle unsupported functions."""
        logger.error("不支持该指令")

    def _handle_confused_function(self):
        """Handle confused functions."""
        logger.error("无法识别指令")

    def json_states_of_all_devices(self) -> str:
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

    def _enter_silent_mode(self):
        logger.info("Enter silent mode.")
        self._close_porcupine()
        self.recognizer.stop_recognizer_sync()
        self.stop_keyword_recognizers()

    def _exit_silent_mode(self):
        logger.info("Exit silent mode.")
        self._init_porcupine()
        self.activate_keyword_recognizers()

    def _call_callback(self, callback: Optional[Callable]):
        """Call the callback function if it's not None."""
        if callback:
            callback()

    def _setup_keyword_recognizers(self):
        """Set up keyword recognizers with models and callbacks."""
        for key, items in self.keyword_recognizers.items():
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

    def activate_keyword_recognizers(self):
        """Activate all keyword recognizers except keep-alive ones."""
        self.speaker.play_start_record()
        self.recognizer.stop_recognizer_sync()
        self.recognizer.start_recognizer()
        for key, items in self.keyword_recognizers.items():
            if key not in self.independent_keyword_list:
                items["recognizer"].recognize_once_async(items["model"])
        self._reset_response_time_counter()
        self.is_activated = True

    def activate_response_keyword_recognizers(self):
        """Activate response-related keyword recognizers."""
        for key in self.independent_keyword_list:
            item = self.keyword_recognizers[key]
            item["recognizer"].recognize_once_async(item["model"])
        self._reset_response_time_counter()
        self.speaker.play_start_record()

    def stop_keyword_recognizers(self):
        """Stop keyword recognizers."""
        for key, items in self.keyword_recognizers.items():
            if key not in self.independent_keyword_list:
                items["recognizer"].stop_recognition_async().get()

    async def response_timer_demon(self):
        """Stop non-keep-alive keyword recognizers after timeout."""
        while True:
            if self._response_time_counter > 0:
                while self._response_time_counter > 0:
                    self._response_time_counter -= self.RESPONSE_INTERVAL
                    logger.debug(
                        "AI_Server.response_time_counter:",
                        self._response_time_counter,
                    )
                    await asyncio.sleep(self.RESPONSE_INTERVAL)
                self.stop_keyword_recognizers()
                self.recognizer.stop_recognizer()
                self.speaker.play_end_record()
                self.is_activated = False
            await asyncio.sleep(self.RESPONSE_INTERVAL)

    @property
    def _response_time_counter(self):
        return getattr(self.__class__, "response_time_counter", 0)

    @_response_time_counter.setter
    def _response_time_counter(self, value):
        setattr(self.__class__, "response_time_counter", value)

    def _reset_response_time_counter(self):
        self._response_time_counter = self.RESPONSE_TIMEOUT

    def set_response_value(self, val):
        """Set the user response value."""
        self.response_user = val

    @staticmethod
    def _canceled_keyword_cb(keyword: str) -> Callable:
        """Create a callback for canceled keyword recognition."""

        def canceled_keyword_cb(evt):
            result = evt.result
            if result.reason == speechsdk.ResultReason.Canceled:
                logger.info(f"{keyword} CANCELED: {result.cancellation_details.reason}")

        return canceled_keyword_cb

    def _recognized_keyword_cb(
        self,
        keyword: str,
        recognizer: speechsdk.KeywordRecognizer,
        keyword_model: speechsdk.KeywordRecognitionModel,
        callback: Callable,
    ) -> Callable:
        """Create a callback for recognized keyword."""

        def recognized_keyword_cb(self: AI_Server, evt):
            result = evt.result
            if result.reason == speechsdk.ResultReason.RecognizedKeyword:
                if len(keyword) < self.recognizer.get_max_len_recogized_words():
                    return
                self.recognizer.stop_recognizer()
                logger.info("RECOGNIZED KEYWORD: {}".format(result.text))
                self = AI_Server.__new__(AI_Server)
                self._reset_response_time_counter()
                callback()
                recognizer.recognize_once_async(keyword_model)

        return lambda evt: recognized_keyword_cb(self, evt)

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
                    self.speaker.speak_text(
                        "警告！当前室内甲醛浓度为{}mg/m3，建议您立即开窗通风。".format(
                            result["mgm3"]
                        )
                    )
                    await asyncio.sleep(180)
            await asyncio.sleep(61)

    def sync_task(self, stop_event: asyncio.Event):
        """A sample synchronous task running in a separate thread."""
        logger.debug("同步任务已启动")
        while not stop_event.is_set():
            logger.debug("同步任务正在运行...")
        logger.debug("同步任务已停止")

    async def main(self):
        """Main function to coordinate all tasks."""
        stop_event = asyncio.Event()
        executor = ThreadPoolExecutor(max_workers=1)

        await self.ws_client_esp32.connect()
        tasks = [
            self.response_timer_demon(),
            # self.monitor_tem_hum(),
            self.monitor_ch2o(),
            self.ws_client_esp32.receive_messages(),
            self.ws_client_esp32.sample_tem_hum(),
            self.ws_client_esp32.heartbeat_task(),
            self.speaker.keep_alive_playback(),
            # asyncio.to_thread(self.sync_task, stop_event),
        ]

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.warning("The program is interrupted by the user.")
        finally:
            await self.ws_client_esp32.close()
            self.stop_keyword_recognizers()
            self.recognizer.stop_recognizer()
            self.task_scheduler.stop()
            self._close_porcupine()
            stop_event.set()
            executor.shutdown()
            self.speaker.close()
            logger.info("The program has been terminated.")


AI = AI_Server(configure_path="./configure.json")

if __name__ == "__main__":
    logger.info(AI.get_states_of_all_devices())
    try:
        asyncio.run(AI.main())
    except KeyboardInterrupt:
        logger.info("程序已停止")
    except Exception as e:
        logger.exception(f"发生错误: {e}")
