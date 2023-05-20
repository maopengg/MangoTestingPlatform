# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-20 19:40
# @Author : 毛鹏
import winreg


def get_installed_paths():
    # 定义查询注册表的路径和键
    reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    reg_key = winreg.HKEY_LOCAL_MACHINE
    # 打开注册表
    with winreg.OpenKey(reg_key, reg_path) as reg:
        # 获取子键数量
        subkey_count = winreg.QueryInfoKey(reg)[0]
        # 定义软件安装路径列表
        paths = []
        # 循环遍历子键
        for i in range(subkey_count):
            # 获取子键名称
            subkey_name = winreg.EnumKey(reg, i)
            # 根据子键名称打开子键
            with winreg.OpenKey(reg, subkey_name) as subkey:
                try:
                    # 获取 DisplayName 和 InstallLocation 值
                    display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                    install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                    # 如果 InstallLocation 值存在，则将软件安装路径添加到列表中
                    if install_location:
                        paths.append(install_location)
                except:
                    pass
        return paths


# 调用函数获取所有软件的安装路径，以列表的方式呈现出来
installed_paths = get_installed_paths()
print(installed_paths)
