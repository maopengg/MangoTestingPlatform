"""Read-only Argo rollout guard; never print manifests, environment values or credentials."""
import argparse
import json
import re
import subprocess
import sys
import time


class RolloutPending(ValueError):
    """A valid workload exists but its controller status has not converged."""


def workload_identity(workload):
    metadata = workload.get('metadata', {})
    values = [metadata.get('namespace', 'unknown'), workload.get('kind', 'unknown'),
              metadata.get('name', 'unknown')]
    return '/'.join(re.sub(r'[^A-Za-z0-9_.-]', '_', str(value))[:253] for value in values)


def rollout_summary(workload):
    # 只输出资源标识和数值白名单，不能输出容器环境或完整 manifest。
    spec, status = workload.get('spec', {}), workload.get('status', {})
    fields = {
        'spec.replicas': spec.get('replicas', 1),
        'metadata.generation': workload.get('metadata', {}).get('generation'),
        'status.replicas': status.get('replicas'),
        'status.observedGeneration': status.get('observedGeneration'),
        'status.readyReplicas': status.get('readyReplicas'),
        'status.updatedReplicas': status.get('updatedReplicas'),
        'status.availableReplicas': status.get('availableReplicas'),
    }
    def display(value):
        if value is None:
            return '缺失'
        return str(value) if type(value) is int else '无效'
    return workload_identity(workload) + ': ' + ', '.join(
        f'{name}={display(value)}' for name, value in fields.items())


def read_argocd(*args):
    result = subprocess.run(['argocd', 'app', *args], capture_output=True, text=True, timeout=45, check=True)
    return json.loads(result.stdout)


def verify_workloads(workloads, expected_image, *, allow_disabled_scheduler=False):
    repository = expected_image.rsplit(':', 1)[0]
    scheduler_found = False
    backend_found = False
    pending = []
    for workload in workloads:
        if not isinstance(workload, dict):
            raise ValueError('无法识别 Argo 工作负载返回结构，不能确认部署成功')
        spec = workload.get('spec', {})
        status = workload.get('status', {})
        if not isinstance(spec, dict) or not isinstance(status, dict) or not isinstance(workload.get('metadata', {}), dict):
            raise ValueError('无法识别 Argo 工作负载字段结构，不能确认部署成功')
        containers = spec.get('template', {}).get('spec', {}).get('containers', [])
        for container in containers:
            image = container.get('image', '')
            environment = {item.get('name'): item.get('value') for item in container.get('env', [])}
            command = ' '.join(container.get('command', []) + container.get('args', []))
            scheduler = ('run_scheduler' in command.split()
                         or environment.get('MANGO_SERVICE_NAME') == 'scheduler-service')
            backend = (image.rsplit(':', 1)[0] == repository or scheduler
                       or environment.get('MANGO_SERVICE_NAME') in
                       {'core-api', 'api-worker', 'mcp-service', 'realtime-service', 'monitoring-service'})
            if not backend:
                continue
            backend_found = True
            if image != expected_image:
                raise ValueError(f'{workload_identity(workload)}: 后端工作负载未全部更新到本次镜像，部署不能判为成功')
            mcp = 'run_mcp_service' in command.split() or environment.get('MANGO_SERVICE_NAME') == 'mcp-service'
            if mcp:
                if 'run_mcp_service' not in command.split():
                    raise ValueError(f'{workload_identity(workload)}: MCP必须显式使用run_mcp_service启动才能执行发布排空，请同步部署配置仓库的command')
                pod_spec = spec.get('template', {}).get('spec', {})
                grace = pod_spec.get('terminationGracePeriodSeconds', 30)
                if type(grace) is not int or grace < 360:
                    raise ValueError(f'{workload_identity(workload)}: MCP发布排空需要terminationGracePeriodSeconds至少360秒，请同步部署配置仓库，旧默认30秒会中断执行')
                for probe_name in ('readinessProbe', 'startupProbe'):
                    if container.get(probe_name, {}).get('httpGet', {}).get('path') != '/health/ready':
                        raise ValueError(f'{workload_identity(workload)}: MCP缺少/health/ready发布排空探针，请同步部署配置仓库的{probe_name}')
            desired = spec.get('replicas', 1)
            if scheduler and allow_disabled_scheduler and type(desired) is int and desired == 0:
                scheduler_found = True
                generation = workload.get('metadata', {}).get('generation')
                observed = status.get('observedGeneration')
                counts = [status.get(field, 0) for field in
                          ('replicas', 'readyReplicas', 'updatedReplicas', 'availableReplicas')]
                if (type(generation) is not int or type(observed) is not int or observed < generation
                        or any(type(value) is not int or value != 0 for value in counts)):
                    pending.append(rollout_summary(workload) + '; 等待 scheduler 完成停用')
                else:
                    print(f'{workload_identity(workload)}: 已按开发环境策略停用（replicas=0），跳过运行就绪探针检查')
                continue
            if type(desired) is not int or desired < 1:
                raise ValueError(f'{rollout_summary(workload)}; 后端目标副本必须大于 0，请确认部署配置中的启停策略')
            generation = workload.get('metadata', {}).get('generation')
            observed, ready, updated = (status.get(field) for field in
                                        ('observedGeneration', 'readyReplicas', 'updatedReplicas'))
            complete = (all(type(value) is int for value in (generation, observed, ready, updated))
                        and observed >= generation and ready >= desired and updated >= desired)
            if not complete:
                pending.append(rollout_summary(workload))
            if workload.get('kind') == 'StatefulSet' and (
                    not status.get('currentRevision') or status['currentRevision'] != status.get('updateRevision')):
                pending.append(f'{workload_identity(workload)}: StatefulSet currentRevision/updateRevision 缺失或不一致')
            if scheduler:
                scheduler_found = True
                probe = container.get('readinessProbe', {}).get('exec', {}).get('command', [])
                if 'check_scheduler' not in probe:
                    raise ValueError(f'{workload_identity(workload)}: scheduler 缺少清理消费者就绪探针，请在部署配置仓库配置 python manage.py check_scheduler')
    if not backend_found or not scheduler_found:
        raise ValueError('未找到后端及独立 scheduler 工作负载，请检查部署配置仓库，不能仅凭 API 健康判断部署成功')
    if pending:
        raise RolloutPending('后端工作负载尚未完成本次镜像更新，不能确认部署成功\n' + '\n'.join(dict.fromkeys(pending)))


def verify(app, expected_image, *, allow_disabled_scheduler=False):
    application = read_argocd('get', app, '-o', 'json')
    resources = application.get('status', {}).get('resources', [])
    workloads = []
    for item in resources:
        if item.get('group') == 'apps' and item.get('kind') in ('Deployment', 'StatefulSet'):
            workloads.append(read_argocd('get-resource', app, '--group', 'apps', '--kind', item['kind'],
                                        '--resource-name', item['name'], '-o', 'json'))
    verify_workloads(workloads, expected_image, allow_disabled_scheduler=allow_disabled_scheduler)


def wait_for_runtime(app, expected_image, *, attempts=4, retry_interval=5, allow_disabled_scheduler=False):
    for attempt in range(1, attempts + 1):
        try:
            verify(app, expected_image, allow_disabled_scheduler=allow_disabled_scheduler)
            return
        except RolloutPending as error:
            print(f'运行状态校验第 {attempt}/{attempts} 次未就绪：{error}', file=sys.stderr, flush=True)
            if attempt == attempts:
                raise
            time.sleep(retry_interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--attempts', type=int, default=4)
    parser.add_argument('--retry-interval', type=int, default=5)
    parser.add_argument('--allow-disabled-scheduler', action='store_true', help='仅用于开发环境中明确设为 0 副本的 scheduler')
    args = parser.parse_args()
    if not 1 <= args.attempts <= 12 or not 0 <= args.retry_interval <= 30:
        parser.error('attempts 必须为 1～12，retry-interval 必须为 0～30 秒')
    try:
        wait_for_runtime(args.app, args.image, attempts=args.attempts, retry_interval=args.retry_interval,
                         allow_disabled_scheduler=args.allow_disabled_scheduler)
    except ValueError as error:
        # JSON 解析错误可能包含输入；只输出固定的校验文案。
        message = '无法读取部署运行状态，已停止确认部署成功' if isinstance(error, json.JSONDecodeError) else str(error)
        parser.exit(1, message + '\n')
    except (OSError, KeyError, TypeError, subprocess.SubprocessError):
        parser.exit(1, '无法只读核验 Argo 工作负载，请检查 Argo CLI 权限与连接；未输出配置内容\n')
    print('后端镜像、工作负载及当前环境的 scheduler 启停策略校验通过')


if __name__ == '__main__':
    main()
