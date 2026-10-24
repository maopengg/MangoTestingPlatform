import math

ALLOWED_CONTROL_TYPES = {
    "mouse_move",
    "mouse_click",
    "mouse_down",
    "mouse_up",
    "mouse_wheel",
    "keyboard_press",
    "keyboard_down",
    "keyboard_up",
    "text_input",
    "pick_element",
    "check_locator",
    "record_action",
    "record_poll",
    "list_pages",
    "switch_page",
    "close_page",
}


class LiveStreamControlEventValidator:
    BUTTONS = {"left", "right", "middle"}
    POINTER_EVENTS = {"mouse_move", "mouse_click", "mouse_down", "mouse_up", "pick_element"}
    BUTTON_EVENTS = {"mouse_click", "mouse_down", "mouse_up"}
    KEY_EVENTS = {"keyboard_press", "keyboard_down", "keyboard_up"}
    PAGE_EVENTS = {"switch_page", "close_page"}
    MAX_TEXT_LENGTH = 2000
    MAX_KEY_LENGTH = 100
    MAX_WHEEL_DELTA = 5000
    RECORD_ACTIONS = {
        "click", "double_click", "right_click", "input", "key_press", "scroll", "drag",
    }

    @classmethod
    def validate(cls, event: dict) -> dict:
        if not isinstance(event, dict):
            raise RuntimeError("远程控制事件格式无效")
        event_type = event.get("event_type")
        if event_type not in ALLOWED_CONTROL_TYPES:
            raise RuntimeError(f"不支持的远程控制事件：{event_type or '-'}")
        normalized = dict(event)
        sequence = cls._integer(event.get("sequence"), "远程控制事件序号")
        if sequence <= 0:
            raise RuntimeError("远程控制事件序号必须大于0")
        normalized["sequence"] = sequence
        if event_type in cls.POINTER_EVENTS:
            normalized["x"] = cls._ratio(event.get("x"), "横坐标")
            normalized["y"] = cls._ratio(event.get("y"), "纵坐标")
        if event_type in cls.BUTTON_EVENTS:
            button = str(event.get("button") or "left")
            if button not in cls.BUTTONS:
                raise RuntimeError("不支持的鼠标按键")
            normalized["button"] = button
        if event_type == "mouse_click":
            click_count = cls._integer(event.get("click_count", 1), "点击次数")
            if click_count not in (1, 2):
                raise RuntimeError("点击次数只支持1或2")
            normalized["click_count"] = click_count
        if event_type == "mouse_wheel":
            normalized["delta_x"] = cls._bounded_number(event.get("delta_x", 0), "横向滚动距离")
            normalized["delta_y"] = cls._bounded_number(event.get("delta_y", 0), "纵向滚动距离")
            if "x" in event or "y" in event:
                normalized["x"] = cls._ratio(event.get("x"), "横坐标")
                normalized["y"] = cls._ratio(event.get("y"), "纵坐标")
        if event_type in cls.KEY_EVENTS:
            key = str(event.get("key") or "")
            if not key or len(key) > cls.MAX_KEY_LENGTH:
                raise RuntimeError("键盘按键为空或超过长度限制")
            normalized["key"] = key
        if event_type == "text_input":
            text = str(event.get("text") or "")
            if len(text) > cls.MAX_TEXT_LENGTH:
                raise RuntimeError("输入文本超过长度限制")
            normalized["text"] = text
        if event_type == "record_action":
            action = str(event.get("action") or "")
            if action not in cls.RECORD_ACTIONS:
                raise RuntimeError("录制动作类型无效")
            normalized["action"] = action
            if action in {"click", "double_click", "right_click", "drag"}:
                normalized["x"] = cls._ratio(event.get("x"), "横坐标")
                normalized["y"] = cls._ratio(event.get("y"), "纵坐标")
            if action == "drag":
                normalized["to_x"] = cls._ratio(event.get("to_x"), "拖动目标横坐标")
                normalized["to_y"] = cls._ratio(event.get("to_y"), "拖动目标纵坐标")
            if action == "input":
                text = str(event.get("text") or "")
                if len(text) > cls.MAX_TEXT_LENGTH:
                    raise RuntimeError("录制输入文本超过长度限制")
                normalized["text"] = text
            if action == "key_press":
                key = str(event.get("key") or "")
                if not key or len(key) > cls.MAX_KEY_LENGTH:
                    raise RuntimeError("录制键盘按键为空或超过长度限制")
                normalized["key"] = key
            if action == "scroll":
                normalized["delta_x"] = cls._bounded_number(event.get("delta_x", 0), "横向滚动距离")
                normalized["delta_y"] = cls._bounded_number(event.get("delta_y", 0), "纵向滚动距离")
        if event_type in cls.PAGE_EVENTS:
            page_id = str(event.get("page_id") or "")
            if not page_id:
                raise RuntimeError("浏览器页面ID不能为空")
            normalized["page_id"] = page_id
        return normalized

    @staticmethod
    def _integer(value, name: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise RuntimeError(f"{name}格式无效") from error

    @staticmethod
    def _ratio(value, name: str) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise RuntimeError(f"{name}格式无效") from error
        if not math.isfinite(number) or number < 0 or number > 1:
            raise RuntimeError(f"{name}必须在0到1之间")
        return number

    @classmethod
    def _bounded_number(cls, value, name: str) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise RuntimeError(f"{name}格式无效") from error
        if not math.isfinite(number) or abs(number) > cls.MAX_WHEEL_DELTA:
            raise RuntimeError(f"{name}超过允许范围")
        return number
