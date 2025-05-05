import subprocess

def get_adb_devices():
    """获取ADB设备列表，并将状态转为中文"""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        devices = []
        for line in result.stdout.splitlines():
            if "List of devices" in line or line.strip() == "":
                continue
            parts = line.strip().split("\t")
            if len(parts) == 2:
                device_id = parts[0]
                status_en = parts[1]
                # 将状态转为中文
                status_cn = {
                    "device": "已连接",
                    "unauthorized": "未授权",
                    "offline": "离线",
                    "no permissions": "无权限",
                }.get(status_en, status_en)  # 默认保留原值（如果不在字典中）
                devices.append({"device_id": device_id, "status": status_cn})

        return devices
    except Exception as e:
        print(f"执行ADB命令出错: {e}")
        return []

# 示例调用
devices = get_adb_devices()
for device in devices:
    print(f"设备ID: {device['device_id']}, 状态: {device['status']}")