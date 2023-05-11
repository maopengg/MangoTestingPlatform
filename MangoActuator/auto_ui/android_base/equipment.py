from auto_ui.android_base.android_base import AndroidBase


class UiautomatorEquipmentDevice(AndroidBase):
    """设备操作"""

    def screen_on(self):
        """打开屏幕"""
        self.android.screen_on()
        self.sleep(1)

    def screen_off(self):
        """关闭屏幕"""
        self.android.screen_off()
        self.sleep(1)

    def swipe_left(self):
        """获取屏幕开关状态"""
        self.android.info.get('screenOn')

    def home(self):
        """返回首页"""
        self.android.keyevent("home")

    def back(self):
        """返回一步"""
        self.android.keyevent("back")

    def get_window_size(self):
        """提取屏幕尺寸"""
        w, h = self.android.window_size()
        return w, h

    def push(self, feli_path, catalogue):
        """推送一个文件-未测试"""
        self.android.push(feli_path, catalogue)

    def pull(self, feli_path, catalogue):
        """提取文件-未测试"""
        self.android.pull(feli_path, catalogue)

    def unlock(self):
        """解锁屏幕-未测试"""
        self.android.unlock()
        self.press_home()

    def press_home(self):
        """按home键"""
        self.android.press('home')

    def press_back(self):
        """按back键"""
        self.android.press('back')

    def press_left(self):
        """按left键"""
        self.android.press('left')

    def press_right(self):
        """按right键"""
        self.android.press('right')

    def press_up(self):
        """按up键"""
        self.android.press('up')

    def press_down(self):
        """按down键"""
        self.android.press('down')

    def press_center(self):
        """按center键"""
        self.android.press('center')

    def press_menu(self):
        """按menu键"""
        self.android.press('menu')

    def press_search(self):
        """按search键"""
        self.android.press('search')

    def press_enter(self):
        """按enter键"""
        self.android.press('enter')

    def press_delete(self):
        """按delete键"""
        self.android.press('delete')

    def press_recent(self):
        """按recent键"""
        self.android.press('recent')

    def press_volume_up(self):
        """按volume_up键"""
        self.android.press('volume_up')

    def press_volume_down(self):
        """按volume_down键"""
        self.android.press('volume_down')

    def press_volume_mute(self):
        """按volume_mute键"""
        self.android.press('volume_mute')

    def press_camera(self):
        """按camera键"""
        self.android.press('camera')

    def press_power(self):
        """按power键"""
        self.android.press('power')
