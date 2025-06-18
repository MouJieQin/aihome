import azure.cognitiveservices.speech as speechsdk
from concurrent.futures import ThreadPoolExecutor
import asyncio
import json
from typing import Dict, Optional
from src.ai_server_devices import AIserverDevices
from libs.ai_assistant import AIassistant
from libs.log_config import logger


class AIserver(AIserverDevices):

    def __init__(self, configure_path: str):
        self._load_configuration(configure_path)
        super().__init__(self.configure)
        self._init_ai_assistant()

    def _load_configuration(self, configure_path: str):
        """Load configuration from the given file path."""
        with open(configure_path, mode="r", encoding="utf-8") as f:
            self.configure = json.load(f)

    def _init_ai_assistant(self):
        """Initialize the AI assistant."""
        self.supported_commands = self._create_supported_function()
        supported_commands_ = self._create_supported_function_for_ai_assistant()
        supported_commands_str = json.dumps(supported_commands_, ensure_ascii=False)
        self.ai_assistant = AIassistant(self.configure, supported_commands_str)

    def _recognized_callback(self, cur_recognized_text: str):
        """Callback function for recognized words."""
        self.recognizer.stop_recognizer()
        if len(cur_recognized_text) > 1:
            self.stop_keyword_recognizers()
            self._chat_with_ai_assistant(cur_recognized_text)

    def _chat_with_ai_assistant(self, user_input: str) -> Optional[str]:
        """Chat with AI assistant and return the response."""
        logger.info(f"User input: {user_input}")
        self.speaker.play_send_message()
        response = self.ai_assistant.chat(user_input, self._json_states_of_all_devices)
        logger.info(f"Assistant response: {response}")
        self.speaker.play_receive_response()
        if response:
            self._handle_ai_assistant_response(response)
        return response

    def _handle_ai_assistant_response(self, response: str):
        """Handle AI assistant response."""
        commands = json.loads(response)
        self._ai_assistant_response_callback(commands)

    def _ai_assistant_response_callback(self, commands: Dict):
        """Callback function for AI assistant response."""
        self.speaker.start_speaking_text(commands["あすな"])
        self._ai_assistant_response_callback_imple(commands, self.supported_commands)

    def _ai_assistant_response_callback_imple(self, commands: Dict, commands_: Dict):
        """Handle AI assistant response."""
        try:
            for key, items in commands.items():
                if key != "あすな":
                    if "args" in items.keys():
                        commands_[key]["function"](**items["args"])
                    else:
                        self._ai_assistant_response_callback_imple(
                            items, commands_[key]
                        )
        except Exception as e:
            logger.error(f"Error handling AI assistant response: {e}")
            self.speaker.speak_text("执行指令时发生错误，请检查指令是否正确。")

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
                            "range": "[3000,5700]",
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
                                "default": 26,
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
            "日程安排程序": {
                "添加日程": {
                    "function": self._add_scheduler_task,
                    "args": {
                        "task_name": {
                            "type": "str",
                            "is_necessary": True,
                        },
                        "run_at": {
                            "type": "str",
                            "format": "YYYY-MM-DD HH:MM:SS",
                            "description": "任务的运行时间。",
                            "is_necessary": True,
                        },
                        "interval": {
                            "type": "str|None",
                            "format": "DD HH:MM:SS",
                            "is_necessary": True,
                            "description": "任务的重复间隔，None表示只运行一次。主意是null类型而不是字符串。",
                            "example": {
                                "interval": None,
                            },
                        },
                        "args": {
                            "type": "dict",
                            "is_necessary": True,
                            "description": "任务的参数。和控制家电的回复相同。一定要包含「あすな」参数，到时任务执行时播放。",
                            "example": {
                                "灯光": {"模式": {"args": {"mode": "Cinema Mode"}}},
                                "あすな": "执行日程任务，把灯光调成影院模式，准备享受沉浸式观影体验吧！",
                            },
                        },
                    },
                }
            },
            "甲醛监测": {
                "暂停监测": {
                    "function": self.set_pause_ch2o_monitor_seconds,
                    "args": {
                        "seconds": {
                            "type": "int",
                            "is_necessary": True,
                            "description": "暂停甲醛监测的时间，单位为秒。",
                            "range": "[0, 28800]",
                        }
                    },
                }
            },
            "开启静默": {
                "function": self._enter_silent_mode,
                "description": "进入系统静默模式，在该模式下，无法唤醒「あすな」。",
                "hint": "由于语音输入的影响，用户的输入可能是寂寞模式",
                "args": {},
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
                            "notification": {
                                "name": "通知",
                                "description": "通知用户一些信息，比如在定时任务中。",
                            },
                            "others": {
                                "name": "其它指令",
                                "description": "其它与家电无关但可以做到的指令，比如知识问答。",
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
        elif type == "notification":
            self._handle_notification_function()

    def _handle_notification_function(self):
        """Handle notification functions."""
        logger.info("通知...")

    def _handle_query_function(self):
        """Handle query functions."""
        logger.info("查询家电的状态")

    def _handle_unsupported_function(self):
        """Handle unsupported functions."""
        logger.error("不支持该指令")

    def _handle_confused_function(self):
        """Handle confused functions."""
        logger.error("无法识别指令")

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
            self.porcupine_manager.close_porcupine()
            stop_event.set()
            executor.shutdown()
            self.speaker.close()
            logger.info("The program has been terminated.")
