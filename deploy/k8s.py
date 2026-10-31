"""Render Kubernetes resources from the same normalized deployment configuration."""
import copy
import hashlib
import json
import re
import shlex
from bootstrap import BACKEND_SERVICES, boolean, private_write, render

SECRETS={'MYSQL_PASSWORD','MYSQL_ROOT_PASSWORD','DJANGO_SECRET_KEY','LIVE_STREAM_SIGNING_KEY',
         'MANGO_INITIAL_ADMIN_PASSWORD','MANGO_INITIAL_GUEST_PASSWORD','MINIO_STORAGE_ACCESS_KEY',
         'MINIO_STORAGE_SECRET_KEY','ACTUATOR_PASSWORD'}


def render_k8s(root,v):
    namespace=v['K8S_NAMESPACE']
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',namespace):raise ValueError('K8S_NAMESPACE 格式不合法')
    if v['K8S_SERVICE_TYPE'] not in {'ClusterIP','NodePort','LoadBalancer'}:raise ValueError('K8S_SERVICE_TYPE 不合法')
    if v['K8S_IMAGE_PULL_POLICY'] not in {'Always','IfNotPresent','Never'}:raise ValueError('K8S_IMAGE_PULL_POLICY 不合法')
    if v['K8S_RUNTIME_ACCESS_MODE'] not in {'ReadWriteOnce','ReadWriteMany'}:raise ValueError('K8S_RUNTIME_ACCESS_MODE 不合法')
    for key in ['K8S_RUNTIME_STORAGE_SIZE','K8S_MYSQL_STORAGE_SIZE','K8S_MINIO_STORAGE_SIZE']:
        if not re.fullmatch(r'[1-9][0-9]*(?:Mi|Gi|Ti)',v[key]):raise ValueError(key+' 使用 10Gi 等存储大小')
    for key in ['K8S_IMAGE_PULL_SECRET','K8S_STORAGE_CLASS','K8S_INGRESS_CLASS','K8S_TLS_SECRET']:
        if v[key] and not re.fullmatch(r'[a-z0-9][a-z0-9.-]*',v[key]):raise ValueError(key+' 格式不合法')
    if v['K8S_INGRESS_HOST'] and not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]*',v['K8S_INGRESS_HOST']):raise ValueError('K8S_INGRESS_HOST 只填写主机名')
    if v['K8S_TLS_SECRET'] and not v['K8S_INGRESS_HOST']:raise ValueError('配置 K8S_TLS_SECRET 时必须填写 K8S_INGRESS_HOST')
    if v['K8S_SERVICE_TYPE']=='NodePort' and (not v['K8S_NODE_PORT'].isdigit() or not 30000<=int(v['K8S_NODE_PORT'])<=32767):raise ValueError('K8S_NODE_PORT 必须在 30000 到 32767 之间')
    if not re.fullmatch(r'[a-zA-Z0-9.:-]+',v['K8S_DNS_RESOLVER']):raise ValueError('K8S_DNS_RESOLVER 格式不合法')
    if not re.fullmatch(r'[1-9][0-9]*s',v['K8S_WAIT_TIMEOUT']):raise ValueError('K8S_WAIT_TIMEOUT 使用 300s 等格式')
    compose=render(root,v);services=compose['services'];generated=root/'deploy/generated/k8s'
    common_labels={'app.kubernetes.io/part-of':'mango','app.kubernetes.io/managed-by':'mango-deploy'}
    def meta(name):return {'name':name,'namespace':namespace,'labels':common_labels.copy()}
    def obj(kind,name,spec=None,**fields):
        x={'apiVersion':'apps/v1' if kind in {'Deployment','StatefulSet'} else 'batch/v1' if kind=='Job' else 'networking.k8s.io/v1' if kind=='Ingress' else 'v1','kind':kind,'metadata':meta(name),**fields}
        if spec is not None:x['spec']=spec
        return x
    env=services['mango_server']['environment'].copy();env.pop('MANGO_SERVICE_NAME',None);env.pop('MANGO_SERVICE_INSTANCE',None);env.pop('UVICORN_WORKERS',None)
    foundation=[{'apiVersion':'v1','kind':'Namespace','metadata':{'name':namespace,'labels':common_labels.copy()}}]
    foundation += [obj('ConfigMap','mango-env',data={k:str(x) for k,x in env.items() if k not in SECRETS}),
                   obj('Secret','mango-secrets',type='Opaque',stringData={k:str(x) for k,x in env.items() if k in SECRETS})]
    foundation.append(obj('Secret','mango-infra-secrets',type='Opaque',stringData={'MYSQL_ROOT_PASSWORD':v['MYSQL_ROOT_PASSWORD'],'ACTUATOR_PASSWORD':v['ACTUATOR_PASSWORD']}))
    gateway=(root/'deploy/generated/gateway.conf').read_text().replace('mango_server:','mango-server:').replace('realtime_service:','realtime-service:').replace('mcp_service:','mcp-service:')
    gateway=gateway.replace('resolver 127.0.0.11 valid=30s;','resolver '+v['K8S_DNS_RESOLVER']+' valid=30s;')
    foundation += [obj('ConfigMap','mango-web-config',data={'gateway.conf':gateway,'runtime-config.js':(root/'deploy/generated/runtime-config.js').read_text()}),
                   obj('ConfigMap','mango-deploy-check',data={'deploy_check.py':(root/'deploy/deploy_check.py').read_text()})]
    checksum=hashlib.sha256(json.dumps([v,gateway],sort_keys=True).encode()).hexdigest()
    def pvc_spec(size,mode='ReadWriteOnce'):
        spec={'accessModes':[mode],'resources':{'requests':{'storage':size}}}
        if v['K8S_STORAGE_CLASS']:spec['storageClassName']=v['K8S_STORAGE_CLASS']
        return spec
    foundation.append(obj('PersistentVolumeClaim','mango-runtime',pvc_spec(v['K8S_RUNTIME_STORAGE_SIZE'],v['K8S_RUNTIME_ACCESS_MODE'])))
    def service(name,port,target=None):
        return obj('Service',name,{'selector':{'app':name},'ports':[{'name':'http' if port in [80,8000,8010,8011] else 'tcp','port':port,'targetPort':target or port}]})
    def pod(name,container,volumes=None,backend=False,init=False):
        container=copy.deepcopy(container);container['imagePullPolicy']=v['K8S_IMAGE_PULL_POLICY']
        container.setdefault('resources',{'requests':{'cpu':'50m','memory':'64Mi'}})
        spec={'containers':[container],'restartPolicy':'Never' if init else 'Always'}
        if volumes:spec['volumes']=volumes
        if v['K8S_IMAGE_PULL_SECRET']:spec['imagePullSecrets']=[{'name':v['K8S_IMAGE_PULL_SECRET']}]
        return {'metadata':{'labels':{**common_labels,'app':name},'annotations':{'mango/config-sha256':checksum}},'spec':spec}
    def env_item(name,key=None):return {'name':name,'valueFrom':{'secretKeyRef':{'name':'mango-infra-secrets' if (key or name) in {'MYSQL_ROOT_PASSWORD','ACTUATOR_PASSWORD'} else 'mango-secrets','key':key or name}}}
    def managed_storage(name,svc,port,size,secret_env):
        c={'name':name,'image':svc['image'],'ports':[{'containerPort':port}],'env':secret_env,
           'args':svc['command'],'volumeMounts':[{'name':'data','mountPath':'/var/lib/mysql' if name=='db' else '/data'}]}
        c['readinessProbe']={'tcpSocket':{'port':port},'initialDelaySeconds':10,'periodSeconds':5}
        c['startupProbe']={'tcpSocket':{'port':port},'periodSeconds':5,'failureThreshold':60}
        foundation.extend([service(name,port),obj('StatefulSet',name,{'serviceName':name,'replicas':1,'selector':{'matchLabels':{'app':name}},'template':pod(name,c),
            'volumeClaimTemplates':[{'metadata':{'name':'data'},'spec':pvc_spec(size)}]})])
    if 'db' in services:
        managed_storage('db',services['db'],3306,v['K8S_MYSQL_STORAGE_SIZE'],
            [env_item('MYSQL_ROOT_PASSWORD'),env_item('MYSQL_PASSWORD'),{'name':'MYSQL_USER','value':v['MYSQL_USER']},{'name':'MYSQL_DATABASE','value':v['MYSQL_DATABASE']}])
    if 'minio' in services:
        managed_storage('minio',services['minio'],9000,v['K8S_MINIO_STORAGE_SIZE'],[env_item('MINIO_ROOT_USER','MINIO_STORAGE_ACCESS_KEY'),env_item('MINIO_ROOT_PASSWORD','MINIO_STORAGE_SECRET_KEY')])
    runtime={'name':'runtime','persistentVolumeClaim':{'claimName':'mango-runtime'}}
    check={'name':'preflight','configMap':{'name':'mango-deploy-check'}}
    env_from=[{'configMapRef':{'name':'mango-env'}},{'secretRef':{'name':'mango-secrets'}}]
    jobs={}
    for name,command in [('preflight',['python','/deploy/deploy_check.py']),('migrate',['sh','-ec','mkdir -p /app/runtime/media /app/runtime/actuator; python manage.py migrate --noinput; python manage.py createcachetable django_cache; python manage.py init_system_data'])]:
        c={'name':name,'image':v['SERVER_IMAGE'],'envFrom':env_from,'command':command,'volumeMounts':[{'name':'runtime','mountPath':'/app/runtime'},{'name':'preflight','mountPath':'/deploy','readOnly':True}]}
        jobs[name]=obj('Job','mango-'+name,{'backoffLimit':0,'activeDeadlineSeconds':600,'template':pod('mango-'+name,c,[runtime,check],init=True)})
    backup_env=[{'name':k,'value':v[k]} for k in ['MYSQL_HOST','MYSQL_PORT','MYSQL_DATABASE','MYSQL_USER']]+[env_item('MYSQL_PWD','MYSQL_PASSWORD')]
    backup_command='set -euo pipefail; mkdir -p /backup; f=/backup/before-deploy-$(date +%Y%m%d-%H%M%S).sql; umask 077; mysqldump --host="$MYSQL_HOST" --port="$MYSQL_PORT" --user="$MYSQL_USER" --single-transaction --no-tablespaces "$MYSQL_DATABASE" > "$f"; gzip "$f"'
    c={'name':'backup','image':v['MYSQL_IMAGE'],'env':backup_env,'command':['bash','-ec',backup_command],'volumeMounts':[{'name':'runtime','mountPath':'/backup','subPath':'backups'}]}
    # Ensure the backup directory exists before using a subPath mount.
    c['volumeMounts']=[{'name':'runtime','mountPath':'/app/runtime'}]
    c['command']=['bash','-ec',backup_command.replace('/backup','/app/runtime/backups')]
    jobs['backup']=obj('Job','mango-backup',{'backoffLimit':0,'activeDeadlineSeconds':600,'template':pod('mango-backup',c,[runtime],init=True)})
    workloads=[]
    for key,svc in services.items():
        if key not in BACKEND_SERVICES and not key.startswith('api_worker_') and key not in {'mango-console','mango_gateway','actuator'}:continue
        name=key.replace('_','-');vols=[];mounts=[]
        c={'name':name,'image':svc['image']}
        if key in BACKEND_SERVICES or key.startswith('api_worker_'):
            c['envFrom']=env_from
            c['env']=[{'name':k,'value':str(x)} for k,x in svc['environment'].items() if k in {'MANGO_SERVICE_NAME','MANGO_SERVICE_INSTANCE','UVICORN_WORKERS'}]
            vols=[runtime];mounts=[{'name':'runtime','mountPath':'/app/runtime'}]
            if svc.get('command'):c['command']=shlex.split(svc['command']) if isinstance(svc['command'],str) else svc['command']
            else:c['command']=['uvicorn','src.asgi:application','--host','0.0.0.0','--port','8000','--workers',v['UVICORN_WORKERS'],'--no-access-log']
            if key in {'mango_server','realtime_service','mcp_service'}:
                port=8000 if key=='mango_server' else 8011 if key=='realtime_service' else 8010
                c['ports']=[{'containerPort':port}];foundation.append(service(name,port))
                if key!='mcp_service':
                    probe={'httpGet':{'path':'/management/health' if key=='mango_server' else '/health/ready','port':port},'periodSeconds':10,'timeoutSeconds':5}
                    c['readinessProbe']=probe;c['startupProbe']={**probe,'failureThreshold':60}
        elif key=='mango-console':
            vols=[{'name':'web-config','configMap':{'name':'mango-web-config'}}]
            mounts=[{'name':'web-config','mountPath':'/usr/share/nginx/html/runtime-config.js','subPath':'runtime-config.js','readOnly':True}]
            foundation.append(service(name,80));c['ports']=[{'containerPort':80}]
        elif key=='mango_gateway':
            vols=[{'name':'web-config','configMap':{'name':'mango-web-config'}},runtime]
            mounts=[{'name':'web-config','mountPath':'/etc/nginx/conf.d/default.conf','subPath':'gateway.conf','readOnly':True},
                    {'name':'runtime','mountPath':'/mango-media','subPath':'media','readOnly':True}]
            c['ports']=[{'containerPort':80}]
            c['readinessProbe']={'httpGet':{'path':'/healthz','port':80},'periodSeconds':10,'timeoutSeconds':5}
            public=service(name,80);public['spec']['type']=v['K8S_SERVICE_TYPE']
            if v['K8S_SERVICE_TYPE']=='NodePort':public['spec']['ports'][0]['nodePort']=int(v['K8S_NODE_PORT'])
            foundation.append(public)
        else:
            c['env']=[env_item(k) if k in SECRETS else {'name':k,'value':x.replace('mango_gateway','mango-gateway')} for k,x in svc['environment'].items()]
            c['command']=svc['command'];vols=[runtime];mounts=[{'name':'runtime','mountPath':'/app/runtime','subPath':'actuator'}]
        if mounts:c['volumeMounts']=mounts
        workloads.append(obj('Deployment',name,{'replicas':1,'strategy':{'type':'Recreate'},'selector':{'matchLabels':{'app':name}},'template':pod(name,c,vols)}))
    if v['K8S_INGRESS_HOST']:
        spec={'rules':[{'host':v['K8S_INGRESS_HOST'],'http':{'paths':[{'path':'/','pathType':'Prefix','backend':{'service':{'name':'mango-gateway','port':{'number':80}}}}]}}]}
        if v['K8S_INGRESS_CLASS']:spec['ingressClassName']=v['K8S_INGRESS_CLASS']
        if v['K8S_TLS_SECRET']:spec['tls']=[{'hosts':[v['K8S_INGRESS_HOST']],'secretName':v['K8S_TLS_SECRET']}]
        workloads.append(obj('Ingress','mango',spec))
    for filename,items in [('foundation',foundation),('workloads',workloads),*[(name,[job]) for name,job in jobs.items()]]:
        private_write(generated/(filename+'.json'),json.dumps({'apiVersion':'v1','kind':'List','items':items},ensure_ascii=False,indent=2)+'\n')
    return {'foundation':foundation,'workloads':workloads,'jobs':jobs}
