# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-08-30 14:20
# @Author : 毛鹏
from diskcache import Cache


class PersistentStorageTool:
    """ 文件缓存 """
    cache = Cache()

    @classmethod
    def get_persistent_cache(cls, key: str) -> str | list | dict:
        """
        获取缓存中指定键的值
        :param key: 缓存键
        :return:
        """
        return cls.cache.get(key)

    @classmethod
    def set_persistent_cache(cls, key: str, value: str | list | dict) -> None:
        """
        设置缓存键的值
        :param key: 缓存键
        :param value: 缓存值
        :return:
        """
        cls.cache.set(key, value)

    @classmethod
    def delete_persistent_cache(cls, key: str) -> None:
        """
        删除缓存中指定键的值
        :param key: 缓存键
        :return:
        """
        cls.cache.delete(key)

    @classmethod
    def updatee_persistent_cach(cls, key: str, value: str | list | dict) -> None:
        """
        更新缓存键的值
        如果缓存中存在指定键，则更新其对应的值；如果不存在，则不进行任何操作。
        :param key: 缓存键
        :param value: 缓存值
        :return:
        """
        if key in cls.cache:
            cls.cache[key] = value

    @classmethod
    def contains_persistent_cache(cls, key: str) -> bool:
        """
        检查缓存中是否包含指定键
        :param key: 缓存键
        :return: 如果缓存中包含指定键，返回True；否则返回False
        """
        return key in cls.cache

    @classmethod
    def clear_persistent_cache(cls) -> None:
        """
        清空缓存中的所有键值对
        :return:
        """
        cls.cache.clear()


if __name__ == '__main__':
    # 示例用法
    PersistentStorageTool.set_persistent_cache('name', 'John')
    print(PersistentStorageTool.get_persistent_cache('name'))  # 输出: John
    PersistentStorageTool.updatee_persistent_cach('name', 'Alice')
    print(PersistentStorageTool.get_persistent_cache('name'))  # 输出: Alice
    PersistentStorageTool.delete_persistent_cache('name')
    print(PersistentStorageTool.get_persistent_cache('name'))  # 输出: None
    print(PersistentStorageTool.contains_persistent_cache('name'))  # 输出: False
