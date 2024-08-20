# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-13 14:07
# @Author : 毛鹏
import psutil
from pywinauto.application import Application
import io
import sys
from pywinauto.application import WindowSpecification
#改变标准输出的默认编码
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf8')

#获取进程id
def get_pid(processName):
    for proc in psutil.process_iter():
        try:
            if(proc.name() == processName):
                print(proc.name())
                print(str(proc.pid))
                return proc.pid
        except psutil.NoSuchProcess:
            pass
    return -1;


# def getControlCoords(control):
#     btnRect = control.rectangle();
#     x = btnRect.left + (btnRect.right - btnRect.left) / 2
#     y = btnRect.top + (btnRect.bottom - btnRect.top) / 2
#     print("x={0},y={1}".format(x, y))
#     return (int(x),int(y))



procId=get_pid("WeChat.exe")
if(procId == -1):
    print("WeChat.exe  is not running")




app = Application(backend='uia').connect(process=procId)

# 获取主窗口
main_Dialog: WindowSpecification = app.window(class_name='WeChatMainWndForPC')
#切换到通讯录
btn1=main_Dialog["通讯录"]
btn1.draw_outline(colour='red')
btn1.click_input()


# 搜索联系人
searchKey="文件传输助手"
searchEdit=main_Dialog.Pane13.Edit
searchEdit.draw_outline(colour='red')
searchEdit.click_input()
searchEdit.type_keys(searchKey)


# 选择搜索出的第一个
try:
    selectItem= main_Dialog.child_window(title=searchKey, control_type="ListItem").wrapper_object()
    selectItem.click_input()
except:
    print("对话框已打开")

# 发送消息
sendMsg="this is a test";
inputMsg=main_Dialog.child_window(title="输入",control_type="Edit").wrapper_object()
inputMsg.click_input()
inputMsg.type_keys(sendMsg, with_spaces=True)

sendbtn = main_Dialog['发送(s)']
sendbtn.draw_outline(colour='red')
sendbtn.click_input()
