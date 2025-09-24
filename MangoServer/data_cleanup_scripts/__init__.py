# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据清洗
# @Time   : 2025-01-24 11:36
# @Author : 毛鹏

def data_cleanup(v):
    if v == '4.7':
        from data_cleanup_scripts.v_4_7_2025_01_24 import main_4_7
        main_4_7()
    elif v == '5.5':
        from data_cleanup_scripts.v_5_2_2025_04_13 import main_5_5
        main_5_5()
    elif v == '5.8':
        from data_cleanup_scripts.v_5_8_2025_09_24 import main_5_8
        main_5_8()
