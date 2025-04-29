# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-03-25 22:22
# @Author : 毛鹏
from datetime import datetime

# 格式：YYYY-MM-DD HH:MM:SS（24小时制）
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(current_time, type(current_time))  # 示例输出：2023-10-25 14:30:45