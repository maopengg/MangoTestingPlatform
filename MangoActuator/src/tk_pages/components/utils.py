from __future__ import annotations

from typing import Any, Callable

from .widgets import Combobox


def set_combo_by_value(combo: Combobox, options: list[tuple[Any, str]], value: Any) -> None:
    for index, (option_value, _label) in enumerate(options):
        if str(option_value) == str(value):
            combo.current(index)
            return
    combo.set("")


def combo_value(combo: Combobox, options: list[tuple[Any, str]]) -> Any:
    selected = combo.current()
    return options[selected][0] if selected >= 0 else None


def run_in_thread(callback: Callable[[], Any], complete: Callable[[Any], Any]) -> None:
    import threading

    def worker():
        try:
            result = callback()
        except Exception as error:
            result = error
        complete(result)

    threading.Thread(target=worker, daemon=True).start()
