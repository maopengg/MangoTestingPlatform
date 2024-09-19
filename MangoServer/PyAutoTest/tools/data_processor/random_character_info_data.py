# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-03 10:48
# @Author : 毛鹏

from faker import Faker


class RandomCharacterInfoData:
    """ 随机的人物信息测试数据 """
    faker = Faker(locale='zh_CN')

    @classmethod
    def get_phone(cls) -> int:
        """随机生成手机号码"""
        return cls.faker.phone_number()

    @classmethod
    def get_id_number(cls) -> int:
        """随机生成身份证号码"""
        return cls.faker.ssn()

    @classmethod
    def get_female_name(cls) -> str:
        """女生姓名"""
        return cls.faker.name_female()

    @classmethod
    def get_male_name(cls) -> str:
        """男生姓名"""
        return cls.faker.name_male()

    @classmethod
    def get_simple_profile(cls):
        """获取简单的人物信息"""
        res = cls.faker.simple_profile()
        return str(res)

    @classmethod
    def get_profile(cls):
        """获取带公司的人物信息"""
        res = cls.faker.profile()
        return str(res)

    @classmethod
    def get_email(cls) -> str:
        """生成邮箱"""
        return cls.faker.email()

    @classmethod
    def get_bank_card(cls):
        """银行卡"""
        return cls.faker.credit_card_number()

    @classmethod
    def get_address(cls):
        """带邮政编码的地址"""
        return cls.faker.address()

    @classmethod
    def get_job(cls):
        """获取职称"""
        return cls.faker.job()

    @classmethod
    def get_company(cls):
        """获取公司名称"""
        return cls.faker.company()
