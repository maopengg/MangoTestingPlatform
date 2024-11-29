
class A:
    def __init__(self):
        self.value = 'aaaa'

    def consumer(self, func, *args, **kwargs):

        # 获取所有子类
        subclasses = self.__class__.__subclasses__()
        print(subclasses)
        for subclass in subclasses:
            subclass_instance = subclass()
            method = getattr(subclass_instance, func, None)
            if callable(method):
                # 调用子类的方法
                method(*args, **kwargs)
                return


if __name__ == '__main__':
    a = A()
    a.consumer('b', 'HHHH')  # 调用 B 类中的 b 方法并传入参数
    a.consumer('c', 'YYYY')  # 调用 C 类中的 c 方法并传入参数
