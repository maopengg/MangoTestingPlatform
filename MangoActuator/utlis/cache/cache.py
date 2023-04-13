# coding: utf-8

from diskcache import Cache

from utlis.logs.nuw_logs import get_cache


class CacheDB:
    cache = Cache(get_cache())

    @classmethod
    def set(cls, key, value, expire=300):
        """
        设置一个key缓存
        @param key: key
        @param value: value
        @param expire: 超时时间
        @return: None
        """
        cls.cache.set(key, value, expire=expire, read=True)

    @classmethod
    def get(cls, key):
        """
        获取一个key值
        @param key:
        @return:
        """
        data = cls.cache.get(key)
        return data

    @classmethod
    def touch(cls, name, expire=300, ):
        """
        更新缓存过期时间
        name=key
        expire=过期时间
        """
        result = cls.cache.touch(name, expire=expire)
        return result

    @classmethod
    def add(cls, key, value, expire=300):
        """ 添加缓存，只有缓存中不存在key值，才会成功 """
        cls.cache.add(key, value, expire=expire)

    @classmethod
    def delete(cls, key):
        """
        删除一个key
        @param key:
        @return:
        """
        if cls.cache.delete(key) is True:
            return True
        else:
            return False

    @classmethod
    def pop(cls, key):
        """ 删除缓存的键值 """
        if cls.cache.pop(key) is True:
            return True
        else:
            return False

    @classmethod
    def delete_all_exceed(cls):
        cls.cache.expire()


# def delete_all():
#     time.sleep(3)
#     for f in os.listdir(file):
#         print(f)
#         os.remove(os.path.join(file, f))


if __name__ == '__main__':
    r = CacheDB()
    r.set('name', '毛鹏')
    r.delete('name')
    print(r.get('name'))
    # delete_all()
