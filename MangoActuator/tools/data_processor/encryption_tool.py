# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-11 11:12
# @Author : 毛鹏
import hashlib


class EncryptionTool:
    """ 加密 """

    @classmethod
    def md5_encrypt(cls, string: str) -> str:
        """
        对字符串进行MD5加密
        :param string:加密字符串
        :return:
        """
        # 创建一个MD5对象
        md5 = hashlib.md5()
        # 将字符串转换为字节流并进行加密
        md5.update(string.encode('utf-8'))
        # 获取加密后的结果
        encrypted_string = md5.hexdigest()
        return encrypted_string
