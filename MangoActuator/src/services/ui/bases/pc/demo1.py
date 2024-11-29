import subprocess
from uiautomation import WindowControl, ButtonControl, TextControl
import time

# 打开计算器
subprocess.Popen('calc.exe')

# 等待计算器窗口出现
time.sleep(1)  # 等待一秒以确保计算器启动
calc_window = WindowControl(searchDepth=1, Name='微信')

# 点击数字按钮
def click_number(number):
    button = ButtonControl(searchFrom=calc_window, Name=str(number))
    button.Click()

# 执行加法 5 + 3
click_number(5)
click_number('+')
click_number(3)
click_number('=')

# 获取结果
result = TextControl(searchFrom=calc_window, ClassName='Result')
print('结果:', result.Name)
