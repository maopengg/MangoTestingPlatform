"""Choose a bounded Node heap before starting a frontend image build."""
import argparse
from pathlib import Path
import subprocess
import sys


def linux_memory(path=Path('/proc/meminfo')):
    if not path.exists():
        return None
    values = {}
    for line in path.read_text().splitlines():
        key, value = line.split(':', 1)
        values[key] = int(value.split()[0]) // 1024
    return values.get('MemAvailable', values.get('MemFree', 0)), values.get('SwapFree', 0)


def cgroup_budget(root=Path('/sys/fs/cgroup')):
    limits = []
    for limit, current in [('memory.max', 'memory.current'),
                           ('memory/memory.limit_in_bytes', 'memory/memory.usage_in_bytes')]:
        try:
            maximum = (root / limit).read_text().strip()
            if maximum != 'max' and int(maximum) < 2**60:
                limits.append(max(0, int(maximum) - int((root / current).read_text())) // 2**20)
        except (OSError, ValueError):
            continue
    return min(limits) if limits else None


def choose_heap(value, available=None, daemon_total=None, container_budget=None):
    if value == 'auto':
        heap = 6144
    elif value.isdigit() and 512 <= int(value) <= 65536:
        heap = int(value)
    else:
        raise ValueError('NODE_HEAP_MB 使用 auto 或 512～65536 的整数，在 .env.example 中修改')
    required = heap + 1536
    budgets = [x for x in (daemon_total, container_budget) if x is not None]
    if available is not None:
        budgets.append(sum(available))
    if budgets and min(budgets) < required:
        raise ValueError(f'前端构建资源不足：Node 堆 {heap}MB，另需预留至少 1536MB。请释放内存、增加可用内存/Swap 或提高 Docker 内存限制；也可在构建机器生成镜像。未停止现有服务')
    return heap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('heap')
    args = parser.parse_args()
    try:
        result = subprocess.run(['docker', 'info', '--format', '{{.MemTotal}}'],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15)
        total = int(result.stdout.strip()) // 2**20 if result.returncode == 0 and result.stdout.strip().isdigit() else None
        memory = linux_memory()
        if total is None:
            print('未读取到 Docker 内存上限，请确认 Docker 未设置低于构建需求的限制。', file=sys.stderr)
        heap = choose_heap(args.heap, memory, total, cgroup_budget())
        print(f'前端构建 Node 堆上限：{heap}MB（仅构建使用，不是运行容器内存）', file=sys.stderr)
        if memory is not None and memory[0] < heap + 1536:
            print('物理可用内存偏少，构建可能使用 Swap、耗时增加。', file=sys.stderr)
        if heap < 6144:
            print('提示：当前堆上限低于已验证的 6144MB，大型前端构建仍可能耗尽堆内存。', file=sys.stderr)
        print(heap)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
