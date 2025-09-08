import psutil

# 获取CPU占用百分比
cpu_percent = psutil.cpu_percent(interval=1)  # interval表示采样间隔（秒）
print(f"CPU占用: {cpu_percent}%")

# 获取内存占用百分比
memory_info = psutil.virtual_memory()
memory_percent = memory_info.percent
print(f"内存占用: {memory_percent}%")

# 获取详细信息
print(f"总内存: {memory_info.total / (1024**3):.2f} GB")
print(f"已用内存: {memory_info.used / (1024**3):.2f} GB")
print(f"可用内存: {memory_info.available / (1024**3):.2f} GB")