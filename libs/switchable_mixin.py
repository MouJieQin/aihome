class SwitchableMixin:
    """
    可开关设备Mixin，提供开关控制通用功能
    """

    def __init__(self, entity_id: str):
        """
        初始化可开关设备

        Args:
            entity_id (str): 开关实体ID
        """
        self.entity_id = entity_id

    def turn_on(self) -> None:
        """打开设备"""
        self._call_service("switch", "turn_on", {"entity_id": self.entity_id})

    def turn_off(self) -> None:
        """关闭设备"""
        self._call_service("switch", "turn_off", {"entity_id": self.entity_id})

    def switch(self, value: bool) -> None:
        """
        切换设备状态

        Args:
            value (bool): True为打开，False为关闭
        """
        if value:
            self.turn_on()
        else:
            self.turn_off()

    def get_state(self) -> bool:
        """获取设备状态"""
        state = self.get_entity_state(self.entity_id)
        return state.get("state") == "on"
