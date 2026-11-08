import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parent))
import bootstrap as b
from k8s import render_k8s

ROOT=Path(__file__).parent.parent


def values(**extra):
    return b.resolve({**{x:'sample-secret-'+x for x in b.SECRET_NAMES},**extra})


class UnifiedDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'deploy',self.root/'deploy',ignore=shutil.ignore_patterns('generated','__pycache__'))
        shutil.copy2(ROOT/'.env.example',self.root/'.env.example')

    def test_copied_template_can_prepare_internal_database_without_losing_literals(self):
        shutil.copy2(self.root/'.env.example',self.root/'.env')
        # This is the documented cold-start workflow; no existing database is present.
        with patch.dict(b.DEFAULTS,{'MANGO_DATA_DIR':str(self.root/'data')}):
            raw=b.read_env(self.root/'.env');raw['MANGO_DATA_DIR']=str(self.root/'data')
            (self.root/'.env').write_text('\n'.join(k+'='+repr(v) for k,v in raw.items()))
            v=b.initialize(self.root/'.env')
        self.assertTrue(v['MYSQL_PASSWORD']);self.assertTrue(v['DJANGO_SECRET_KEY'])
        self.assertEqual(b.initialize(self.root/'.env')['MYSQL_PASSWORD'],v['MYSQL_PASSWORD'])

    def test_existing_database_with_missing_password_is_rejected(self):
        data=self.root/'data';(data/'mysql').mkdir(parents=True);(data/'mysql/ibdata1').touch()
        (self.root/'.env').write_text("MYSQL_DATABASE=mango_server\nMANGO_DATA_DIR="+str(data)+'\n')
        with self.assertRaisesRegex(ValueError,'MYSQL_PASSWORD'):b.initialize(self.root/'.env')

    def test_automatic_public_storage_url_is_recomputed_after_site_change(self):
        (self.root/'.env').write_text("FILE_STORAGE_BACKEND=minio\nPUBLIC_URL=http://first.example.com\nMANGO_DATA_DIR="+str(self.root/'data')+'\n')
        first=b.initialize(self.root/'.env')
        self.assertEqual(first['S3_PUBLIC_BASE_URL'],'http://first.example.com/minio/mango-file')
        p=self.root/'.env';p.write_text(p.read_text().replace('http://first.example.com','https://second.example.com'))
        self.assertEqual(b.initialize(p)['S3_PUBLIC_BASE_URL'],'https://second.example.com/minio/mango-file')

    def test_worker_count_is_shared_by_compose_and_kubernetes(self):
        v=values(API_WORKER_COUNT='3')
        d=b.render(self.root,v)
        self.assertIn('api_worker_3',d['services'])
        self.assertEqual(d['services']['api_worker_3']['environment']['MYSQL_PASSWORD'],v['MYSQL_PASSWORD'])
        k=render_k8s(self.root,v)
        self.assertIn('api-worker-3',[x['metadata']['name'] for x in k['workloads']])
        with self.assertRaises(ValueError):values(API_WORKER_COUNT='0')

    def test_scheduler_shares_backend_image_and_has_cleanup_readiness(self):
        for environment in ('dev', 'test', 'master'):
            v=values(DJANGO_ENV=environment,SERVER_IMAGE='registry.example.com/mango-server:new')
            d=b.render(self.root,v)
            scheduler=d['services']['scheduler_service']
            self.assertEqual(scheduler['image'],d['services']['mango_server']['image'])
            self.assertIn('check_scheduler',scheduler['healthcheck']['test'])
            self.assertEqual('--cleanup-only' in scheduler['command'],environment=='dev')
            k=render_k8s(self.root,v)
            resource=next(x for x in k['workloads'] if x['metadata']['name']=='scheduler-service')
            container=resource['spec']['template']['spec']['containers'][0]
            self.assertEqual(container['image'],v['SERVER_IMAGE'])
            self.assertIn('check_scheduler',container['readinessProbe']['exec']['command'])

    def test_images_logging_optional_services_and_binlog_are_configurable(self):
        d=b.render(self.root,values(SERVER_IMAGE='registry.example.com/company/api:release',CONSOLE_IMAGE='registry.example.com/company/web:release'))
        self.assertEqual(d['services']['mango_server']['image'],'registry.example.com/company/api:release')
        self.assertNotIn('monitoring_service',d['services'])
        self.assertIn('--skip-log-bin',d['services']['db']['command'])
        self.assertEqual(d['services']['mango_gateway']['networks']['default']['aliases'],['mango-gateway'])
        for service in d['services'].values():self.assertEqual(service['logging']['options'],{'max-size':'10m','max-file':'1'})
        b.render(self.root,values(MYSQL_MODE='external',MYSQL_HOST='db.example.com',MYSQL_PASSWORD='literal$#value'))
        raw=json.loads((self.root/'deploy/generated/compose.json').read_text())
        self.assertNotIn('db',raw['services'])
        self.assertEqual(raw['services']['mango_server']['environment']['MYSQL_PASSWORD'],'literal$$#value')

    def test_server_addon_routes_and_minio_prefix_survive_rendering(self):
        v=values(FILE_STORAGE_BACKEND='minio',S3_SECRET_KEY='example-object-secret',S3_PUBLIC_BASE_URL='http://platform.example.com:8000/minio/mango-file',PUBLIC_URL='http://platform.example.com:8000',
                 EXTRA_HTTP_ROUTES=json.dumps({'/attendance/':'http://attendance-workbench:80'}))
        b.render(self.root,v);s=(self.root/'deploy/generated/gateway.conf').read_text()
        self.assertIn('location /attendance/',s);self.assertIn('attendance-workbench:80',s)
        self.assertIn('location /minio/',s);self.assertIn('location /mango-file/',s)
        self.assertIn('proxy_pass http://minio:9000/',s)
        self.assertNotIn('auth_basic',s)

    def test_configuration_only_frontend_artifact_is_identical_across_origins(self):
        for api,site in [('/api','http://web.example.com:8001'),('https://api.example.com/api','https://web.example.com')]:
            b.render(self.root,values(FRONTEND_API_BASE=api,PUBLIC_URL=site))
            runtime=(self.root/'deploy/generated/runtime-config.js').read_text()
            self.assertIn(api,runtime)
            for token in ['MYSQL_PASSWORD','sample-secret','S3_SECRET_KEY']:self.assertNotIn(token,runtime)

    def test_k8s_database_storage_matrix_secret_boundaries_and_valid_dns(self):
        for mode in ['internal','external']:
            for storage,place in [('local','internal'),('minio','internal'),('minio','external'),('tos','external')]:
                with self.subTest(mode=mode,storage=storage,place=place):
                    v=values(DEPLOY_TARGET='k8s',MYSQL_MODE=mode,MYSQL_HOST='mysql.example.com',FILE_STORAGE_BACKEND=storage,MINIO_MODE=place,
                             S3_ENDPOINT='s3.example.com',S3_REGION='cn-beijing',S3_BUCKET='sample-bucket',S3_ACCESS_KEY='sample-access',
                             S3_SECRET_KEY='sample-storage-secret',S3_PUBLIC_BASE_URL='https://files.example.com/sample-bucket',
                             SERVER_IMAGE='registry.example.com/mango/api:release',CONSOLE_IMAGE='registry.example.com/mango/web:release')
                    d=render_k8s(self.root,v)
                    names={x['metadata']['name'] for x in d['foundation'] if x['kind']=='StatefulSet'}
                    self.assertEqual('db' in names,mode=='internal')
                    self.assertEqual('minio' in names,storage=='minio' and place=='internal')
                    for x in d['foundation']:
                        if x['kind']=='ConfigMap':
                            self.assertNotIn('sample-storage-secret',json.dumps(x));self.assertNotIn('sample-secret-',json.dumps(x))
                    config=next(x for x in d['foundation'] if x['metadata']['name']=='mango-web-config')
                    self.assertNotIn('mango_server:',config['data']['gateway.conf'])
                    self.assertIn('mango-server:8000',config['data']['gateway.conf'])
                    app_secret=next(x for x in d['foundation'] if x['metadata']['name']=='mango-secrets')
                    self.assertNotIn('MYSQL_ROOT_PASSWORD',app_secret['stringData'])
                    for resource in d['workloads']:
                        self.assertNotIn('_',resource['metadata']['name'])
                        self.assertEqual(resource['spec']['replicas'],1)
                    for path in (self.root/'deploy/generated/k8s').glob('*.json'):self.assertEqual(path.stat().st_mode&0o777,0o600)

    def test_k8s_ingress_pvc_and_opt_in_executor(self):
        d=render_k8s(self.root,values(DEPLOY_TARGET='k8s',ACTUATOR_ENABLED='true',ACTUATOR_PASSWORD='sample-actor-password',
                                     K8S_SERVICE_TYPE='NodePort',K8S_NODE_PORT='30081',K8S_INGRESS_HOST='platform.example.com',
                                     K8S_INGRESS_CLASS='nginx',K8S_TLS_SECRET='platform-tls',K8S_STORAGE_CLASS='shared-files'))
        ingress=next(x for x in d['workloads'] if x['kind']=='Ingress')
        self.assertEqual(ingress['spec']['tls'][0]['secretName'],'platform-tls')
        service=next(x for x in d['foundation'] if x['kind']=='Service' and x['metadata']['name']=='mango-gateway')
        self.assertEqual(service['spec']['ports'][0]['nodePort'],30081)
        self.assertIn('actuator',[x['metadata']['name'] for x in d['workloads']])
        self.assertNotIn('sample-actor-password',json.dumps(next(x for x in d['foundation'] if x['metadata']['name']=='mango-env')))

    def test_invalid_routes_and_k8s_parameters_fail_before_writing_files(self):
        for extra in [{'EXTRA_HTTP_ROUTES':'{"/api/":"http://api.example.com"}'},{'EXTRA_HTTP_ROUTES':'{"/help/":"http://api.example.com; include /tmp/x"}'}]:
            with self.assertRaises(ValueError):values(**extra)
        for extra in [{'K8S_NAMESPACE':'Not A Namespace'},{'K8S_SERVICE_TYPE':'NodePort','K8S_NODE_PORT':'8000'},{'K8S_TLS_SECRET':'tls','K8S_INGRESS_HOST':''}]:
            with self.assertRaises(ValueError):render_k8s(self.root,values(**extra))

    def test_executor_env_defaults_and_explicit_cli_override(self):
        import ast, argparse, contextlib, io
        source=ast.parse((ROOT/'MangoActuator/headless_main.py').read_text())
        functions=[x for x in source.body if isinstance(x,ast.FunctionDef) and x.name=='parse_args']
        scope={'argparse':argparse,'os':os,'DEFAULT_EXECUTOR_PASSWORD':'sample-actor-secret','parse_bool':lambda x:x}
        exec(compile(ast.Module(body=functions,type_ignores=[]),'headless_args','exec'),scope)
        with patch.dict(os.environ,{'ACTUATOR_HOST':'http://gateway:80','ACTUATOR_USERNAME':'open','ACTUATOR_WEB_PARALLEL':'2','ACTUATOR_PYTEST_PARALLEL':'3','ACTUATOR_QUEUE_SIZE':'4'}):
            with patch.object(sys,'argv',['headless_main.py']):args=scope['parse_args']()
            self.assertEqual((args.host,args.username,args.password,args.web_parallel,args.pytest_parallel,args.ui_queue_size),('http://gateway:80','open','sample-actor-secret',2,3,4))
            with patch.object(sys,'argv',['headless_main.py','--host','http://override:8000']):self.assertEqual(scope['parse_args']().host,'http://override:8000')
            output=io.StringIO()
            with patch.object(sys,'argv',['headless_main.py','--help']),contextlib.redirect_stdout(output),self.assertRaises(SystemExit):scope['parse_args']()
            self.assertNotIn('sample-actor-secret',output.getvalue())

    def test_k8s_prepare_never_invokes_docker_or_kubectl(self):
        shutil.copy2(ROOT/'deploy.sh',self.root/'deploy.sh')
        v=values(DEPLOY_TARGET='k8s',PUBLIC_URL='https://platform.example.com')
        (self.root/'.env').write_text('\n'.join(k+'='+repr(value) for k,value in v.items())+'\n')
        result=subprocess.run(['sh','deploy.sh','--prepare-only'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.root/'deploy/generated/k8s/workloads.json').exists())


if __name__=='__main__':unittest.main()
