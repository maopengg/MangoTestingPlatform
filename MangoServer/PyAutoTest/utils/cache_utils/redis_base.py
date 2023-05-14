# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-14 9:28
# @Author : 毛鹏
from django_redis import get_redis_connection


class RedisSting:
    def __init__(self, library: str):
        self.conn = get_redis_connection(library)

    def set_key(self, key, value):
        """写入一个key"""
        self.conn.set(key, value, nx=False)

    def set_key_not(self, key, value):
        """key不存在时写入一个key"""
        self.conn.set(key, value, nx=True)

    def set_key_ex(self, key, value, ex=300):
        """写入一个key,设置过期时间，默认300秒"""
        self.conn.set(key, value, ex)

    def mset_set(self, *args, **kwargs):
        """批量设置-未测试"""
        self.conn.mset(*args, **kwargs)

    def mget_list(self, key_list: list):
        """批量获取"""
        return self.conn.mget(key_list)

    def getset(self, key, value):
        """设置新值并获取原来的值"""
        return self.conn.getset(key, value)

    def get_range(self, key, start, end):
        """获取子序列 start起始位置 end结束位置"""
        return self.conn.getrange(key, start, end)

    def set_range(self, key, offset, value):
        """修改字符串内容，从指定字符串索引开始向后替换（新值太长时，则向后添加）"""
        self.conn.setrange(key, offset, value)

    def strlen(self, key):
        """返回key对应值的字节长度（一个汉字3个字节）"""
        return self.conn.strlen(key)

    def incr(self, key, amount=1):
        """自增 key对应的值，当key不存在时，则创建key＝amount，否则，则自增"""
        self.conn.incr(key, amount=amount)

    def decr(self, key, amount=1):
        """自减 key对应的值，当key不存在时，则创建key＝amount，否则，则自减"""
        self.conn.decr(key, amount)

    def append(self, key, value):
        """在redis key对应的值后面追加内容"""
        self.conn.append(key, value)


class RedisList:

    def __init__(self, library: str):
        self.conn = get_redis_connection(library)

    def left_lpush(self, key, _list: list):
        """在key对应的list中添加元素，每个新的元素都添加到列表的最左边"""
        self.conn.lpush(key, _list)

    def right_rpush(self, key, _list: list):
        """表示从右向左添加"""
        self.conn.rpush(key, _list)

    def linsert(self, key, where, refvalue, value):
        """在key对应的列表的某一个值前或后插入一个新值"""
        self.conn.linsert(key, where, refvalue, value)

    def lset(self, key, index, value):
        """对key对应的list中的某一个索引位置重新赋值"""
        self.conn.lset(key, index, value)

    def lrem(self, key, value, num):
        """在key对应的list中删除指定的值"""
        self.conn.lrem(key, value, num)

    def lpop(self, keys, timeout):
        """在key对应的列表的左侧获取第一个元素并在列表中移除，返回值则是第一个元素"""
        return self.conn.lpop(keys, timeout)

    def lindex(self, key, index):
        """在key对应的列表中根据索引获取列表元素"""
        return self.conn.lindex(key, index)

    def lrange(self, key, start, end):
        """key对应的列表分片获取数据"""
        return self.conn.lrange(key, start, end)

    def ltrim(self, key, start, end):
        """移除不在0--2之间的值"""
        self.conn.ltrim(key, start, end)

    def blpop(self, keys, timeout):
        """将多个列表排列，按照从左到右去pop对应列表的元素"""
        self.conn.blpop(keys, timeout)


class RedisDict:
    def __init__(self, library: str):
        self.conn = get_redis_connection(library)

    def set_hset(self, name, key, value):
        """name对应的hash中设置一个键值对（不存在，则创建；否则，修改）"""
        self.conn.hset(name, key, value)

    def set_hmset(self, name, _dict: dict):
        """在name对应的hash中批量设置键值对"""
        self.conn.hmset(name, _dict)

    def get_hget(self, name, key):
        """在name对应的hash中获取根据key获取value"""
        data = self.conn.hget(name, key)
        return data if data else None

    def get_hmget(self, name, keys: list):
        """在name对应的hash中获取多个key的值"""
        return self.conn.hmget(name, keys)

    def get_hgetall(self, name):
        """获取name对应hash的所有键值"""
        return self.conn.hgetall(name)

    def hlen(self, name):
        """获取name对应的hash中键值对的个数"""
        return self.conn.hlen(name)

    def hkeys(self, name):
        """获取name对应的hash中所有的key的值"""
        return self.conn.hkeys(name)

    def hvals(self, name):
        """获取name对应的hash中所有的value的值"""
        return self.conn.hvals(name)

    def hexists(self, name, key):
        """查name对应的hash是否存在当前传入的key"""
        return self.conn.hexists(name, key)

    def hdel(self, name, *keys):
        """将name对应的hash中指定key的键值对删除"""
        self.conn.hdel(name, *keys)

    def hincrby(self, name, key, amount=1):
        """自增name对应的hash中的指定key的值，不存在则创建key=amount"""
        self.conn.hincrby(name, key, amount)

    def hscan_iter(self, name, match=None, count=None):
        """利用yield封装hscan创建生成器，实现分批去redis中获取数据"""
        return self.conn.hscan_iter(name, count=10000)

    def l_scan(self, name, count=1000):
        cursor = 0
        while True:
            if cursor >= self.conn.llen(name):
                break
            ret = self.conn.lrange(name, cursor, count + cursor - 1)
            cursor += count
            for i in ret:
                yield i


class RedisBase(RedisSting, RedisList, RedisDict):

    def delete(self, *names):
        """根据删除redis中的任意数据类型"""
        self.conn.delete(*names)

    def exists(self, name):
        """检测redis的name是否存在"""
        return True if self.conn.exists(name) else False

    def keys(self, key):
        """模糊查询key值"""
        res = self.conn.keys(f'{key}?')
        if res:
            return res
        res = self.conn.keys(f'{key}*')
        return res

    def pipeline(self, key: list, value: list):
        """管道(模拟事务)"""
        pipe = self.conn.pipeline(transaction=True)
        pipe.multi()
        for k, v in zip(key, value):
            pipe.set(k, v)
        pipe.execute()

    def delete_all_(self):
        """删除库里所有的key"""
        self.conn.flushdb()

    def all_keys(self):
        return self.conn.keys('*')
