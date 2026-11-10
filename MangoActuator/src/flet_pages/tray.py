from __future__ import annotations

from pathlib import Path
from typing import Callable


class TrayController:
    """Optional pystray integration; failure leaves the normal window usable."""

    def __init__(self, icon_path: str, show: Callable[[], None], exit_app: Callable[[], None]):
        self.icon_path = Path(icon_path)
        self.show_callback = show
        self.exit_callback = exit_app
        self.icon = None

    @property
    def available(self) -> bool:
        return self.icon is not None

    def start(self) -> bool:
        try:
            import pystray
            from PIL import Image

            image = Image.open(self.icon_path)
            self.icon = pystray.Icon(
                "mango-actuator", image, "芒果执行器",
                menu=pystray.Menu(
                    pystray.MenuItem("显示窗口", lambda _icon, _item: self.show_callback(), default=True),
                    pystray.MenuItem("退出", lambda _icon, _item: self.exit_callback()),
                ),
            )
            self.icon.run_detached()
            return True
        except Exception:
            self.icon = None
            return False

    def stop(self) -> None:
        if self.icon:
            self.icon.stop()
            self.icon = None
