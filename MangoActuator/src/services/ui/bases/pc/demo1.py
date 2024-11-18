# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-13 11:09
# @Author : 毛鹏
# -*- coding: utf-8 -*-
# this script only works with Win32 notepad.exe
# if you notepad.exe is the Windows Store version in Windows 11, you need to uninstall it.
import subprocess

import uiautomation as auto


def test():
    subprocess.Popen('notepad.exe', shell=True)
    # 首先从桌面的第一层子控件中找到记事本程序的窗口WindowControl，再从这个窗口查找子控件
    notepadWindow = auto.WindowControl(searchDepth=1, ClassName='Notepad')
    notepadWindow.SetTopmost(True)
    # 查找notepadWindow所有子孙控件中的第一个EditControl，因为EditControl是第一个子控件，可以不指定深度
    edit = notepadWindow.EditControl()
    try:
        # 获取EditControl支持的ValuePattern，并用Pattern设置控件文本为"Hello"
        edit.GetValuePattern().SetValue('Hello')  # or edit.GetPattern(auto.PatternId.ValuePattern)
    except auto.comtypes.COMError as ex:
        # 如果遇到COMError, 一般是没有以管理员权限运行Python, 或者这个控件没有实现pattern的方法(如果是这种情况，基本没有解决方法)
        # 大多数情况不需要捕捉COMError，如果遇到了就加到try block
        pass
    edit.SendKeys('{Ctrl}{End}{Enter}World')  # 在文本末尾打字
    # 先从notepadWindow的第一层子控件中查找TitleBarControl,
    # 然后从TitleBarControl的子孙控件中找第二个ButtonControl, 即最大化按钮，并点击按钮
    notepadWindow.TitleBarControl(Depth=1).ButtonControl(foundIndex=2).Click()
    # 从notepadWindow前两层子孙控件中查找Name为'关闭'的按钮并点击按钮
    notepadWindow.ButtonControl(searchDepth=2, Name='关闭').Click()
    # 这时记事本弹出是否保存提示，按热键Alt+N不保存退出。
    auto.SendKeys('{Alt}n')


if __name__ == '__main__':
    test()
