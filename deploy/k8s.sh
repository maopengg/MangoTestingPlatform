#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
command -v kubectl >/dev/null || { echo '请先安装 kubectl 并选择目标集群上下文。' >&2; exit 1; }
NAMESPACE=$(python3 deploy/bootstrap.py get .env.example K8S_NAMESPACE --target k8s)
TIMEOUT=$(python3 deploy/bootstrap.py get .env.example K8S_WAIT_TIMEOUT --target k8s)
k() { kubectl -n "$NAMESPACE" "$@"; }
kubectl apply -f deploy/generated/k8s/foundation.json >/dev/null
for name in db minio; do
    if k get statefulset "$name" >/dev/null 2>&1; then k rollout status statefulset/"$name" --timeout="$TIMEOUT"; fi
done
run_job() {
    name=$1
    if k get job "mango-$name" >/dev/null 2>&1; then
        OWNER=$(k get job "mango-$name" -o 'jsonpath={.metadata.labels.app\.kubernetes\.io/managed-by}')
        [ "$OWNER" = mango-deploy ] || { echo '检测到同名非本部署任务，停止。' >&2; exit 1; }
        k delete job "mango-$name" --wait=true >/dev/null
    fi
    k apply -f "deploy/generated/k8s/$name.json" >/dev/null
    if ! k wait --for=condition=complete "job/mango-$name" --timeout="$TIMEOUT"; then
        echo "K8s $name 任务未完成；未继续后续部署。请在集群检查任务事件和日志（不要公开凭据）。" >&2
        exit 1
    fi
}
run_job preflight
# Include every managed API worker, including workers removed by a lower count.
STOP_NAMES=$(k get deployments -l app.kubernetes.io/managed-by=mango-deploy -o 'jsonpath={range .items[*]}{.metadata.name}{"\n"}{end}')
for name in $STOP_NAMES; do
    case "$name" in mango-console) continue ;; esac
    if k get deployment "$name" >/dev/null 2>&1; then
        OWNER=$(k get deployment "$name" -o 'jsonpath={.metadata.labels.app\.kubernetes\.io/managed-by}')
        [ "$OWNER" = mango-deploy ] || { echo '检测到同名非本部署服务，停止。' >&2; exit 1; }
        k scale deployment "$name" --replicas=0 >/dev/null
        k wait --for=delete pod -l "app=$name" --timeout="$TIMEOUT"
    fi
done
run_job backup
run_job migrate
k apply -f deploy/generated/k8s/workloads.json >/dev/null
for name in $(python3 - <<'PY'
import json
print(' '.join(x['metadata']['name'] for x in json.load(open('deploy/generated/k8s/workloads.json'))['items'] if x['kind']=='Deployment'))
PY
); do k rollout status "deployment/$name" --timeout="$TIMEOUT"; done
echo 'K8s 部署完成，数据库、存储及初始化已通过；请按 .env.example 的 Service/Ingress 配置验证公网入口。'
