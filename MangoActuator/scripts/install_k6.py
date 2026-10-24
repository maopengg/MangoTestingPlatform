#!/usr/bin/env python3
import sys
from pathlib import Path


ACTUATOR_ROOT = Path(__file__).resolve().parents[1]
if str(ACTUATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ACTUATOR_ROOT))

from src.services.perf.k6_runtime import ensure_k6_available  # noqa: E402


def main() -> int:
    try:
        binary = ensure_k6_available()
    except Exception as error:
        print(f"k6 安装失败：{error}", file=sys.stderr)
        return 1
    if not binary:
        print("当前系统或架构不支持自动安装 k6", file=sys.stderr)
        return 1
    print(f"k6 已就绪：{binary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
