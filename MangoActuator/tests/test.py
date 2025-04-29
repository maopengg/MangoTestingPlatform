# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-01-06 18:32
# @Author : 毛鹏

from mangokit.database import MysqlConnect
from mangokit.models import MysqlConingModel
mysql = MysqlConnect(MysqlConingModel(host='localhost', port=3306, user='root', password='mP123456&', database='dev_mango_server'))
sql = """
INSERT INTO `dev_mango_server`.`ui_case` (`id`, `create_time`, `update_time`, `name`, `case_flow`, `status`, `level`, `front_custom`, `front_sql`, `posterior_sql`, `case_people_id`, `module_id`, `project_product_id`, `parametrize`, `switch_step_open_url`) VALUES (4, '2025-12-02 16:40:32.106722', '2025-04-29 09:22:18.292501', '断言演示', '->测试切换', 0, 0, '[]', '[]', '[]', 1, 1, 1, '[]', 0);

"""
print(mysql.execute(sql))