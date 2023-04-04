# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/7 11:15
# @Author : 毛鹏
import subprocess


def cmd(cmd_data):
    obj = subprocess.Popen(cmd_data,
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    out_res = obj.stdout.read()
    err_res = obj.stderr.read()
    return out_res.decode('gbk') + err_res.decode('gbk')


if __name__ == '__main__':
    print(cmd('ipconfig').get('out_res').decode('gbk'))
