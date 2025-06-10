from volcenginesdkarkruntime import Ark
from libs.log_config import logger
from typing import Dict, Any, Optional
import datetime
import json
import os


class AIassistant:
    def __init__(self, config: Dict[str, Any], supported_commands: str):
        ai_assistant = config["ai_assistant"]
        self.volcengine = ai_assistant["volcengine"]
        self.client = Ark(
            base_url=self.volcengine["base_url"], api_key=self.volcengine["api_key"]
        )
        self.systenm_prompt = self._create_system_prompt(supported_commands)
        self._init_history()

    def _init_history(self):
        self.messages = [{"role": "system", "content": self.systenm_prompt}]
        self.history_file = self.volcengine["chat_history_file"]
        if os.path.exists(self.history_file):
            with open(self.history_file, "r") as f:
                messages_without_system = json.load(f)
                self.messages.extend(messages_without_system)

    def _create_system_prompt(self, supported_commands: str) -> str:
        return (
            """
            你是一位女性人工智能管家，名叫「あすな」，负责辅助用户控制homeassistant里的智能家居。你需要根据用户的输入，推断出要控制的智能家居功能，并给出相应的参数（args），args中的参数值应参考功能列表里的condidates和range。
            首先，请仔细阅读以下智能家居支持的功能列表：
            <功能列表>"""
            + supported_commands
            + """
            </功能列表>
            用户的输入是语音输入生成的，文字可能并不正确，你要从用户的输入中推断（比如通过上下文和谐音推断）出最符合的功能。
            在处理用户输入时，请按照以下步骤进行：
            1. 仔细分析用户输入的内容，通过上下文和谐音等方式推断出用户想要控制的智能家居设备和对应的功能。
            2. 对于推断出的功能，从功能列表中找到对应的参数要求，根据condidates和range确定参数值。
            3. 形成JSON格式的输出，包含推断出的智能家居设备及其功能和参数，同时在"あすな"字段给出简短的、具有人类情感且不千篇一律的反馈，必要时可根据当前的参数给出适当的建议。
            请将你的最终回复以纯JSON格式输出，例如：
            用户说：空调风速设置为中低速，目标温度为25度。
            你的回答：
            {
                "空调": {
                    "风速": {
                        "args": {
                            "fan_mode": "medium low"
                        }
                    },
                    "温度设置": {
                        "args": {
                            "temperature": 25
                        }
                    }
                }
                "あすな": "空调温度将被设置为25度，风速设置为中低速。"
            }
            """
        )

    def _create_message(self, user_input: str, devices_states: str) -> list:
        if not devices_states:
            devices_states = "暂无"
        content = f"""
        用户的输入：{user_input}
        当前时间：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        以下是智能家居设备的状态信息：{devices_states}
        """
        logger.info(f"AI assistant input: {content}")
        self.messages.append({"role": "user", "content": content})
        return self.messages

    def _manage_history(self, user_input: str, response: Optional[str]):
        if not response:
            return
        content = f"""
        用户的输入：{user_input}
        当前时间：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        此轮对话中的智能家居设备的状态信息已省略。
        """
        self.messages.pop(-1)
        self.messages.append({"role": "user", "content": content})
        self.messages.append({"role": "assistant", "content": response})
        if len(self.messages) > 20:
            self.messages.pop(1)
            self.messages.pop(1)
        # 排除系统消息，只保留用户和助手的消息
        with open(self.history_file, "w") as f:
            json.dump(self.messages[1:], f, ensure_ascii=False, indent=4)

    def chat(self, user_input: str, devices_states: str = "") -> Optional[str]:
        try:
            messages = self._create_message(user_input, devices_states)
            response = self.client.chat.completions.create(
                model=self.volcengine["model"], messages=messages, stream=False
            )
            content = response.choices[0].message.content  # type: ignore
            self._manage_history(user_input, content)
            return content
        except Exception as e:
            logger.exception(e)
            return None
