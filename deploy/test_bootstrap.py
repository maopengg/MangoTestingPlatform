import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('bootstrap',Path(__file__).with_name('bootstrap.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def config(**extra):
    return b.resolve({**{k:'test-secret-'+k for k in b.SECRET_NAMES},**extra})


class DeploymentConfigurationTests(unittest.TestCase):
    def test_first_run_and_repeat_preserve_all_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'.env'
            first=b.initialize(path)
            second=b.initialize(path)
            self.assertEqual(first,second)
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            self.assertNotEqual(first['MYSQL_PASSWORD'],first['MYSQL_ROOT_PASSWORD'])

    def test_legacy_file_migration_preserves_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'.env'
            (path.with_name('.env.deploy')).write_text('\n'.join(k+'=old-'+k for k in b.SECRET_NAMES))
            result=b.initialize(path)
            self.assertEqual(result['MYSQL_PASSWORD'],'old-MYSQL_PASSWORD')
            self.assertTrue(path.exists())

    def test_existing_external_password_never_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'.env';path.write_text('MYSQL_MODE=external\nMYSQL_HOST=mysql.example.com\n')
            before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'MYSQL_PASSWORD'): b.initialize(path)
            self.assertEqual(before,path.read_bytes())

    def test_parser_preserves_special_characters_without_shell_expansion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'.env';path.write_text("PASSWORD='a$# b\\c=\"d'\nNAME=value # note\nEMPTY=\n")
            self.assertEqual(b.read_env(path),{'PASSWORD':'a$# b\\c="d','NAME':'value','EMPTY':''})

    def test_duplicate_and_bad_quotes_rejected_without_echoing_values(self):
        for source in ['A=secret\nA=secret\n',"A='secret\n",'bad line secret']:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'.env';path.write_text(source)
                with self.assertRaises(ValueError) as caught:b.read_env(path)
                self.assertNotIn('secret',str(caught.exception))

    def test_invalid_ports(self):
        for key in ['WEB_PORT','MYSQL_PORT','API_PORT']:
            for value in ['0','65536','bad']:
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    config(MYSQL_MODE='external',MYSQL_HOST='db.example.com',**{key:value})

    def test_same_front_and_api_port_rejected(self):
        with self.assertRaises(ValueError):config(API_PORT='8000')

    def test_internal_root_user_rejected_but_external_root_supported(self):
        with self.assertRaises(ValueError):config(MYSQL_USER='root')
        self.assertEqual(config(MYSQL_MODE='external',MYSQL_HOST='db.example.com',MYSQL_USER='root')['MYSQL_USER'],'root')

    def test_legacy_external_host_infers_mode(self):
        self.assertEqual(config(MYSQL_HOST='db.example.com')['MYSQL_MODE'],'external')

    def test_nginx_injection_and_mixed_content_rejected(self):
        for extra in [{'BACKEND_UPSTREAM':'http://api.example.com;include /tmp/config'},
                      {'PUBLIC_URL':'https://web.example.com','FRONTEND_API_BASE':'http://api.example.com/api'},
                      {'PUBLIC_URL':'https://web.example.com','FRONTEND_SOCKET_URL':'ws://api.example.com/ws/'}]:
            with self.subTest(extra=extra),self.assertRaises(ValueError):config(**extra)

    def test_storage_required_fields(self):
        with self.assertRaisesRegex(ValueError,'S3_'):config(FILE_STORAGE_BACKEND='tos')
        with self.assertRaises(ValueError):config(FILE_STORAGE_BACKEND='unknown')

    def render(self,v):
        root=Path(tempfile.mkdtemp());self.addCleanup(__import__('shutil').rmtree,root)
        (root/'deploy/nginx').mkdir(parents=True)
        (root/'deploy/compose.single.json').write_bytes(Path(__file__).with_name('compose.single.json').read_bytes())
        (root/'deploy/nginx/single-server.conf').write_bytes(Path(__file__).parent.joinpath('nginx/single-server.conf').read_bytes())
        d=b.render(root,v)
        return root,d

    def test_mysql_and_storage_matrix(self):
        for mode in ['internal','external']:
            for storage,place in [('local','internal'),('minio','internal'),('minio','external'),('tos','external')]:
                with self.subTest(mode=mode,storage=storage,place=place):
                    v=config(MYSQL_MODE=mode,MYSQL_HOST='db.example.com' if mode=='external' else 'db',
                       FILE_STORAGE_BACKEND=storage,MINIO_MODE=place,S3_ENDPOINT='s3.example.com',
                       S3_REGION='cn-beijing',S3_BUCKET='example-bucket',S3_ACCESS_KEY='access-value',
                       S3_SECRET_KEY='storage-secret-value',S3_PUBLIC_BASE_URL='https://files.example.com/example-bucket')
                    root,d=self.render(v)
                    self.assertEqual('db' in d['services'],mode=='internal')
                    self.assertEqual('minio' in d['services'],storage=='minio' and place=='internal')
                    for name,service in d['services'].items():
                        if service.get('image')=='mango-server:single':
                            self.assertEqual(service['environment']['MYSQL_HOST'],v['MYSQL_HOST'])
                            self.assertEqual(service['environment']['MYSQL_PASSWORD'],v['MYSQL_PASSWORD'])
                    public=(root/'deploy/generated/runtime-config.js').read_text()
                    self.assertNotIn('storage-secret-value',public)
                    self.assertNotIn('access-value',public)
                    self.assertNotIn(v['MYSQL_PASSWORD'],public)
                    self.assertEqual((root/'deploy/generated/compose.json').stat().st_mode&0o777,0o600)
                    for service in d['services'].values():
                        for dep in service.get('depends_on',{}):self.assertIn(dep,d['services'])

    def test_same_origin_and_split_ports(self):
        root,d=self.render(config(WEB_PORT='8001',API_PORT='8000',PUBLIC_URL='http://web.example.com:8001'))
        public=(root/'deploy/generated/runtime-config.js').read_text()
        self.assertIn('"apiBase": "/api"',public)
        self.assertIn('ws://web.example.com:8001/ws/web/socket?',public)
        self.assertEqual(len(d['services']['mango_gateway']['ports']),2)

    def test_cross_origin_socket_and_proxy(self):
        root,d=self.render(config(PUBLIC_URL='https://web.example.com',FRONTEND_API_BASE='https://api.example.com/api',
                                  BACKEND_UPSTREAM='http://backend.example.com:8000'))
        self.assertIn('wss://api.example.com/ws/web/socket?',(root/'deploy/generated/runtime-config.js').read_text())
        self.assertIn('proxy_pass http://backend.example.com:8000',(root/'deploy/generated/gateway.conf').read_text())
        self.assertEqual(d['services']['mango_server']['environment']['CORS_ALLOWED_ORIGINS'],'https://web.example.com')

    def test_password_dollar_is_escaped_in_compose_only(self):
        root,d=self.render(config(MYSQL_PASSWORD='a$# b'))
        self.assertEqual(d['services']['mango_server']['environment']['MYSQL_PASSWORD'],'a$# b')
        raw=json.loads((root/'deploy/generated/compose.json').read_text())
        self.assertEqual(raw['services']['mango_server']['environment']['MYSQL_PASSWORD'],'a$$# b')

    def test_internal_minio_signed_url_preserves_host_and_bucket_path(self):
        root,d=self.render(config(FILE_STORAGE_BACKEND='minio',S3_SECRET_KEY='minio-secret'))
        nginx=(root/'deploy/generated/gateway.conf').read_text()
        self.assertIn('location /mango-file/',nginx)
        # Keep the API /mango-file/ local-media route separate from the object bucket route.
        self.assertEqual(nginx.count('location /mango-file/'),1)


if __name__=='__main__':unittest.main()

class DeploymentScriptTests(unittest.TestCase):
    def test_external_database_script_never_starts_db_and_config_only_skips_builds(self):
        import shutil
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copytree(Path(__file__).parent,root/'deploy',ignore=shutil.ignore_patterns('__pycache__','generated'))
            shutil.copy2(Path(__file__).parent.parent/'deploy.sh',root/'deploy.sh')
            shutil.copy2(Path(__file__).parent.parent/'.env.example',root/'.env.example')
            data=root/'data'
            values=config(MYSQL_MODE='external',MYSQL_HOST='db.example.com',MANGO_DATA_DIR=str(data))
            (root/'.env').write_text('\n'.join(k+'='+"'"+v+"'" for k,v in values.items())+'\n')
            executable=root/'bin/docker';executable.parent.mkdir()
            log=root/'commands.log'
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_DOCKER_LOG"\nexit 0\n')
            executable.chmod(0o755)
            import os
            with patch.dict(os.environ,{'PATH':str(executable.parent)+os.pathsep+os.environ['PATH'],'TEST_DOCKER_LOG':str(log)}):
                subprocess.run(['sh','deploy.sh'],cwd=root,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            calls=log.read_text()
            self.assertNotIn('build mango-console',calls)
            self.assertNotIn('build mango_server',calls)
            self.assertNotIn('up -d --wait --wait-timeout 180 db',calls)
            self.assertNotIn('exec -T db',calls)
            self.assertIn('run -T --rm --no-deps db_tools',calls)
            self.assertIn('deploy_check.py',calls)
            self.assertNotIn('test-secret-MYSQL_PASSWORD',calls)
