"""Use real local Git remotes and simulate Docker only."""
import json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import bootstrap as b
ROOT=Path(__file__).parent.parent

class DeploymentFixture(unittest.TestCase):
 def git(self,*args,cwd):
  return subprocess.run([self.real_git,*args],cwd=cwd,capture_output=True,text=True,check=True).stdout.strip()
 def identity(self,p):
  self.git('config','user.name','Deployment Test',cwd=p);self.git('config','user.email','deployment@example.com',cwd=p)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  base=Path(self.tmp.name);self.root=base/'checkout';self.root.mkdir();self.remote=base/'remote.git';self.peer=base/'peer';self.real_git=shutil.which('git')
  self.git('init','--bare',str(self.remote),cwd=base);self.git('init','-b','master',cwd=self.root);self.identity(self.root)
  shutil.copytree(ROOT/'deploy',self.root/'deploy',ignore=shutil.ignore_patterns('generated','__pycache__'))
  for p in ['deploy.sh','.env.example']:shutil.copy2(ROOT/p,self.root/p)
  (self.root/'.gitignore').write_text('.env\n/deploy/generated/\n/data/\n/bin/\n/docker.log\n/git.log\n/image.json\n')
  for rel,text in [('MangoServer/src/probe.py','value=1\n'),('MangoServer/src/settings/dev.py',"MYSQL_IP='original.db.example.com'\n"),('mango-console/probe.js','export const value=1\n')]:
   p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
  self.git('add','.',cwd=self.root);self.git('commit','-m','initial fixture',cwd=self.root);self.git('remote','add','origin',str(self.remote),cwd=self.root);self.git('push','-u','origin','master',cwd=self.root)
  self.git('clone','--branch','master',str(self.remote),str(self.peer),cwd=base);self.identity(self.peer)
  revision=self.git('rev-parse','HEAD',cwd=self.root)
  (self.root/'image.json').write_text(json.dumps({'Id':'sha256:fixture','Config':{'Labels':{'org.opencontainers.image.revision':revision}}}))
  v=b.resolve({**{k:'sample-only-'+k for k in b.SECRET_NAMES},'MYSQL_MODE':'external','MYSQL_HOST':'db.example.com','MANGO_DATA_DIR':str(self.root/'data')})
  (self.root/'.env').write_text('\n'.join(k+"='"+x+"'" for k,x in v.items())+'\n')
  bin_dir=self.root/'bin';bin_dir.mkdir()
  scripts={'docker':'''import json,os,sys
args=sys.argv[1:]
with open(os.environ['TEST_DOCKER_LOG'],'a') as f:f.write(json.dumps(args)+'\\n')
if args[:2]==['image','inspect']:
 if os.getenv('TEST_BROKEN_IMAGE'):print('invalid-json')
 else:print(json.dumps([json.load(open(os.environ['TEST_IMAGE']))]))
if os.getenv('TEST_HEALTH_FAIL') and '--spider' in args:sys.exit(1)
''','git':'''import json,os,sys
args=sys.argv[1:]
if args[:1]==['pull']:
 with open(os.environ['TEST_GIT_LOG'],'a') as f:f.write(json.dumps(args)+'\\n')
 if os.getenv('TEST_PULL_FAIL'):sys.exit(1)
os.execv(os.environ['TEST_REAL_GIT'],[os.environ['TEST_REAL_GIT'],*args])
'''}
  for name,script in scripts.items():
   p=bin_dir/name;p.write_text('#!'+sys.executable+'\n'+script);p.chmod(0o755)
  self.env={'PATH':str(bin_dir)+os.pathsep+os.environ['PATH'],'TEST_DOCKER_LOG':str(self.root/'docker.log'),'TEST_GIT_LOG':str(self.root/'git.log'),'TEST_REAL_GIT':self.real_git,'TEST_IMAGE':str(self.root/'image.json')}
 def update_remote(self,rel,text):
  p=self.peer/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
  self.git('add',rel,cwd=self.peer);self.git('commit','-m','fixture update',cwd=self.peer);self.git('push',cwd=self.peer)
 def run_deploy(self,*args,extra=None):
  for name in ['docker.log','git.log']:(self.root/name).unlink(missing_ok=True)
  with patch.dict(os.environ,{**self.env,**(extra or {})}):return subprocess.run(['sh','deploy.sh',*args],cwd=self.root,capture_output=True,text=True)
 def commands(self):
  p=self.root/'docker.log';return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
 def builds(self):return [x[-1] for x in self.commands() if 'build' in x]

class DeploymentSyncTests(DeploymentFixture):
 def test_default_pulls_once_and_reuses_matching_images(self):
  r=self.run_deploy();self.assertEqual(r.returncode,0,r.stderr)
  self.assertEqual(json.loads((self.root/'git.log').read_text()),['pull','--ff-only']);self.assertEqual(self.builds(),[])
  self.assertTrue((self.root/'deploy/generated/last-success.json').exists())
 def test_remote_backend_update_is_pulled_and_rebuilt(self):
  self.update_remote('MangoServer/src/probe.py','value=2\n');r=self.run_deploy();self.assertEqual(r.returncode,0,r.stderr)
  self.assertEqual((self.root/'MangoServer/src/probe.py').read_text(),'value=2\n');self.assertEqual(self.builds(),['mango_server'])
 def test_dependency_update_rebuilds_backend_shared_with_scheduler(self):
  self.update_remote('MangoServer/requirements/base.txt','redis==6.4.0\ngreenlet>=3.1,<4\n');r=self.run_deploy();self.assertEqual(r.returncode,0,r.stderr)
  self.assertEqual(self.builds(),['mango_server'])
  services=json.loads((self.root/'deploy/generated/compose.json').read_text())['services']
  self.assertEqual(services['mango_server']['image'],services['scheduler_service']['image'])
 def test_already_pulled_frontend_update_still_rebuilds(self):
  self.assertEqual(self.run_deploy().returncode,0);self.update_remote('mango-console/probe.js','export const value=2\n');self.git('pull','--ff-only',cwd=self.root)
  r=self.run_deploy();self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(self.builds(),['mango-console'])
 def test_build_option_survives_script_reload(self):
  r=self.run_deploy('--build');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(self.builds(),['mango_server','mango-console']);self.assertEqual(len((self.root/'git.log').read_text().splitlines()),1)
 def test_pull_failure_does_not_touch_docker_or_env(self):
  before=(self.root/'.env').read_bytes();r=self.run_deploy(extra={'TEST_PULL_FAIL':'1'});self.assertNotEqual(r.returncode,0);self.assertEqual(self.commands(),[]);self.assertEqual((self.root/'.env').read_bytes(),before)
 def test_conflicting_local_change_is_not_overwritten(self):
  self.update_remote('MangoServer/src/probe.py','value=2\n');p=self.root/'MangoServer/src/probe.py';p.write_text('value=3\n')
  r=self.run_deploy();self.assertNotEqual(r.returncode,0);self.assertEqual(p.read_text(),'value=3\n');self.assertEqual(self.commands(),[])
 def test_local_environment_file_survives_unrelated_pull(self):
  p=self.root/'MangoServer/src/settings/dev.py';p.write_text("MYSQL_IP='custom.db.example.com'\n");self.update_remote('README.md','Updated fixture\n')
  r=self.run_deploy();self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(p.read_text(),"MYSQL_IP='custom.db.example.com'\n");self.assertEqual(self.builds(),['mango_server'])
 def test_inspection_error_stops_before_services_are_stopped(self):
  r=self.run_deploy(extra={'TEST_BROKEN_IMAGE':'1'});self.assertNotEqual(r.returncode,0);self.assertFalse(any('stop' in x for x in self.commands()));self.assertFalse((self.root/'deploy/generated/last-success.json').exists())
 def test_failed_health_check_does_not_record_success(self):
  r=self.run_deploy(extra={'TEST_HEALTH_FAIL':'1'});self.assertNotEqual(r.returncode,0);self.assertFalse((self.root/'deploy/generated/last-success.json').exists())
