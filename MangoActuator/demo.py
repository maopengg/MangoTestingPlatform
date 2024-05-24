import asyncio

import psutil

# 内存使用率阈值(%)
MEMORY_THRESHOLD = 80


async def my_task():
    """模拟一个异步任务"""
    while True:
        print("执行任务中...1")
        await asyncio.sleep(3)
        print("执行任务中...2")


async def monitor_memory():
    """监控内存使用率,并暂停/恢复任务"""
    task = asyncio.create_task(my_task())
    is_paused = False
    while True:
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > MEMORY_THRESHOLD:
            if not is_paused:
                print(f"内存使用率过高 ({memory_percent}%), 暂停任务...")
                await task
                is_paused = False
        else:
            if is_paused:
                print(f"内存使用率正常 ({memory_percent}%), 恢复任务...")
                task = asyncio.create_task(my_task())
                is_paused = True
        await asyncio.sleep(5)  # 5秒检查一次内存使用率
        print('')


async def main():
    """主函数"""
    await asyncio.gather(
        monitor_memory()
    )


if __name__ == "__main__":
    asyncio.run(main())
