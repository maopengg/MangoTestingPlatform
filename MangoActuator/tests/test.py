import subprocess


def get_adb_devices():
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
                devices.append({"device_id": parts[0], "status": parts[1]})

        return devices
    except Exception as e:
        print(f"执行 ADB 命令出错: {e}")
        return []


# 示例调用
devices = get_adb_devices()
for device in devices:
    print(f"设备ID: {device['device_id']}, 状态: {device['status']}")
