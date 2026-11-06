"""Read-only Argo rollout guard; never print manifests, environment values or credentials."""
import argparse
import json
import subprocess


def read_argocd(*args):
    result = subprocess.run(['argocd', 'app', *args], capture_output=True, text=True, timeout=45, check=True)
    return json.loads(result.stdout)


def verify_workloads(workloads, expected_image):
    repository = expected_image.rsplit(':', 1)[0]
    scheduler_found = False
    backend_found = False
    for workload in workloads:
        if not isinstance(workload, dict):
            raise ValueError('无法识别 Argo 工作负载返回结构，不能确认部署成功')
        spec = workload.get('spec', {})
        status = workload.get('status', {})
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
                raise ValueError('后端工作负载未全部更新到本次镜像，部署不能判为成功')
            desired = spec.get('replicas', 1)
            if (desired < 1 or status.get('readyReplicas', 0) < desired
                    or status.get('observedGeneration', 0) < workload.get('metadata', {}).get('generation', 1)
                    or status.get('updatedReplicas', 0) < desired):
                raise ValueError('后端工作负载尚未完成本次镜像更新，不能确认部署成功')
            if workload.get('kind') == 'StatefulSet' and (
                    not status.get('currentRevision') or status['currentRevision'] != status.get('updateRevision')):
                raise ValueError('后端 StatefulSet 仍有旧版本副本，不能确认部署成功')
            if scheduler:
                scheduler_found = True
                if spec.get('replicas', 1) < 1 or status.get('readyReplicas', 0) < 1:
                    raise ValueError('scheduler 没有就绪副本，数据工厂清理任务可能无人消费')
                probe = container.get('readinessProbe', {}).get('exec', {}).get('command', [])
                if 'check_scheduler' not in probe:
                    raise ValueError('scheduler 缺少清理消费者就绪探针，请在部署配置仓库配置 python manage.py check_scheduler')
    if not backend_found or not scheduler_found:
        raise ValueError('未找到后端及独立 scheduler 工作负载，请检查部署配置仓库，不能仅凭 API 健康判断部署成功')


def verify(app, expected_image):
    application = read_argocd('get', app, '-o', 'json')
    resources = application.get('status', {}).get('resources', [])
    workloads = []
    for item in resources:
        if item.get('group') == 'apps' and item.get('kind') in ('Deployment', 'StatefulSet'):
            workloads.append(read_argocd('get-resource', app, '--group', 'apps', '--kind', item['kind'],
                                        '--resource-name', item['name'], '-o', 'json'))
    verify_workloads(workloads, expected_image)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', required=True)
    parser.add_argument('--image', required=True)
    args = parser.parse_args()
    try:
        verify(args.app, args.image)
    except ValueError as error:
        # JSON 解析错误可能包含输入；只输出固定的校验文案。
        message = '无法读取部署运行状态，已停止确认部署成功' if isinstance(error, json.JSONDecodeError) else str(error)
        parser.exit(1, message + '\n')
    except (OSError, KeyError, TypeError, subprocess.SubprocessError):
        parser.exit(1, '无法只读核验 Argo 工作负载，请检查 Argo CLI 权限与连接；未输出配置内容\n')
    print('后端镜像一致，scheduler 副本及清理消费者就绪探针已确认')


if __name__ == '__main__':
    main()
