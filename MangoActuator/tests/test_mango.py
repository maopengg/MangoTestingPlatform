# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-02 16:21
# @Author : 毛鹏
from mangokit import *


def test_001(is_send=False):
    if is_send:
        text = '哈哈哈，测试内容！'
        Mango.s(text)


def test_002():
    value = 'haha'
    key = '${key}'
    processor = DataProcessor()
    processor.set_cache('key', value)
    assert processor.replace(key) == value


def test_003():
    url = 'https://www.baidu.com/home/feed/feedwater?id=2&offset=1&sessionId=&crids=&req_type=1&bsToken=47b1e832d560175c274525ef2c36828d&pos=&newsNum=&needAd=1&refresh_state=-1&ismain=1&indextype=manht&_req_seqid=0xf534052f012fd953&asyn=1&t=1727853777386&sid=60271_60826_60784'
    assert requests.get(url).text == '{"errMsg":"缺失参数","errno":10000}'


def test_004():
    mysql_connect = MysqlConnect(MysqlConingModel(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='mP123456&',
        database='mango_server',
    ))
    result = mysql_connect.execute('SHOW TABLES;')
    assert result == 42


def test_005():
    from mangokit.tools import InitPath
    connect = SQLiteConnect(InitPath.cache)
    connect.execute('''CREATE TABLE IF NOT EXISTS my_table (id INTEGER PRIMARY KEY, name TEXT)''')
    connect.execute("INSERT INTO my_table (name) VALUES ('test_name')")
    result = connect.execute("SELECT * FROM my_table WHERE name='test_name'")
    assert result is not None, "数据不存在"
    connect.execute("DROP TABLE my_table")


if __name__ == '__main__':
    test_001(True)
    test_002()
    test_003()
    test_004()
    test_005()
