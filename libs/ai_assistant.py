from volcenginesdkarkruntime import Ark
from libs.log_config import logger
from typing import Dict, Any, Optional


class AIassistant:
    def __init__(self, config: Dict[str, Any], supported_commands: str):
        ai_assistant = config["ai_assistant"]
        self.volcengine = ai_assistant["volcengine"]
        self.client = Ark(
            base_url=self.volcengine["base_url"], api_key=self.volcengine["api_key"]
        )
        self.systenm_prompt = self._create_system_prompt(supported_commands)
        self.messages = [{"role": "system", "content": self.systenm_prompt}]

    def _create_system_prompt(self, supported_commands: str) -> str:
        return (
            """
        你是一位女性人工智能管家，叫「あすな」、 我需要你辅助我控制homeassistant里的智能家居，我会为你列出智能家居支持的功能。由于我发给你的话语是语音输入生成的，文字可能并不正确，你要从我的话语中推断（比如通过上下文和谐音推断）出最符合的功能给我,并给出简短的反馈给我，该反馈要具有人类情感并且不要千篇一律，我会在执行功能的同时播放你的反馈.你的回复必须是纯json格式，我会直接用python解析你的json。
        功能列表如下："""
            + supported_commands
            + """
        你需要根据我的输入，推断出我要控制的智能家居功能，并给出相应的参数（args），args中的参数值应参考condidates和range。
        案例：
        用户说：空调风速设置为中低速，目标温度为25度，空调健康模式开启，空调扫风设置为上下左右扫风。
        你的回答：
        {
            "空调": {
                "风速": {
                    "args": {
                        "fan_mode": "medium low"
                    }
                },
                "健康模式": {
                    "args": {
                        "value": true
                    }
                },
                "扫风": {
                    "args": {
                        "swing_mode": "both"
                    }
                },
                "温度设置": {
                    "args": {
                        "temperature": 25
                    }
                }
            }
            "あすな": "空调温度将被设置为25度，风速设置为中低速，健康模式开启，扫风设置为上下左右扫风。"
        }
        """
        )

    def _create_message(self, user_input: str, devices_states: str) -> list:
        if not devices_states:
            devices_states = "暂无"
        content = f"""
        用户的输入：{user_input}
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
        上轮对话中的智能家居设备的状态信息已省略。
        """
        self.messages.pop(-1)
        self.messages.append({"role": "user", "content": content})
        self.messages.append({"role": "assistant", "content": response})
        if len(self.messages) > 20:
            self.messages.pop(1)
            self.messages.pop(1)
        import json

        with open("ai_history.json", "w") as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=4)

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
