# coding: utf-8

from diskcache import Cache
from utlis.logs.nuw_logs import get_cache


class CacheDB:

    def __init__(self):
        self.cache = Cache(get_cache())

    def set(self, key, value, expire=300):
        self.cache.set(key, value, expire=expire, read=True)

    def get(self, key):
        data = self.cache.get(key)
        return data

    def touch(self, name, expire=300, ):
        """
        更新缓存过期时间
        name=key
        expire=过期时间
        """
        result = self.cache.touch(name, expire=expire)
        return result

    def add(self, key, value, expire=300):
        """ 添加缓存，只有缓存中不存在key值，才会成功 """
        self.cache.add(key, value, expire=expire)

    def delete(self, key):
        if self.cache.delete(key) is True:
            return True
        else:
            return False

    def pop(self, key):
        """ 删除缓存的键值 """
        if self.cache.pop(key) is True:
            return True
        else:
            return False

    def delete_all_exceed(self):
        self.cache.expire()


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
