"""Ensure legacy configuration remains authoritative and is never rewritten."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parent))
import bootstrap as b
from k8s import render_k8s
ROOT=Path(__file__).parent.parent

class SettingsDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'deploy',self.root/'deploy',ignore=shutil.ignore_patterns('generated','__pycache__'))
        shutil.copy2(ROOT/'.env.example',self.root/'.env.example')
        self.settings=self.root/'MangoServer/src/settings';self.settings.mkdir(parents=True)
        for env in ['dev','test','master']:
            (self.settings/(env+'.py')).write_text("MYSQL_IP='"+env+".db.example.com'\nMYSQL_PORT=3307\nMYSQL_DB_NAME='sample_db'\nMYSQL_USER='sample_user'\nMYSQL_PASSWORD='source$#password'\n")
        (self.root/'.env').write_text('MYSQL_MODE=settings\nDJANGO_ENV=dev\nMYSQL_HOST=ignored.example.com\nMYSQL_PASSWORD=ignored-password\nMANGO_DATA_DIR='+str(self.root/'data')+'\n')

    def test_source_wins_without_rewriting_or_copying_credentials_to_env(self):
        original={p:p.read_bytes() for p in self.settings.glob('*.py')}
        v=b.initialize(self.root/'.env')
        self.assertEqual(v['MYSQL_HOST'],'dev.db.example.com')
        self.assertEqual(v['MYSQL_PASSWORD'],'source$#password')
        self.assertEqual(b.read_env(self.root/'.env')['MYSQL_PASSWORD'],'ignored-password')
        d=b.render(self.root,v)
        self.assertNotIn('db',d['services'])
        self.assertNotIn('db',d['services']['mango_server'].get('depends_on',{}))
        self.assertEqual(d['services']['db_tools']['environment']['MYSQL_PWD'],'source$#password')
        for p,data in original.items():self.assertEqual(p.read_bytes(),data)
        k=render_k8s(self.root,v)
        self.assertFalse(any(x['kind']=='StatefulSet' and x['metadata']['name']=='db' for x in k['foundation']))
        self.assertEqual(b.initialize(self.root/'.env')['MYSQL_PASSWORD'],'source$#password')

    def test_modified_master_source_is_reloaded_without_regenerating_files(self):
        b.initialize(self.root/'.env')
        raw=b.read_env(self.root/'.env');raw['DJANGO_ENV']='master'
        self.assertEqual(b.resolve(raw,self.root)['MYSQL_HOST'],'master.db.example.com')
        p=self.settings/'master.py';p.write_text(p.read_text().replace('source$#password','updated$#password'))
        self.assertEqual(b.resolve(raw,self.root)['MYSQL_PASSWORD'],'updated$#password')
        self.assertEqual(b.resolve({**raw,'DJANGO_ENV':'prod'},self.root)['MYSQL_PASSWORD'],'updated$#password')

    def test_optional_local_database_json_is_respected(self):
        p=self.settings/'dev.py';p.write_text(p.read_text()+"\nimport json\nwith open('src/settings/database.json') as f:\n MYSQL_IP=json.load(f)['mysql_ip']\n")
        j=self.settings/'database.json';j.write_text(json.dumps({'mysql_ip':'private.db.example.com'}));original=j.read_bytes()
        self.assertEqual(b.initialize(self.root/'.env')['MYSQL_HOST'],'private.db.example.com')
        self.assertEqual(j.read_bytes(),original)

    def test_missing_or_invalid_source_fails_without_changing_env(self):
        before=(self.root/'.env').read_bytes();(self.settings/'dev.py').unlink()
        with self.assertRaisesRegex(ValueError,'DJANGO_ENV'):b.initialize(self.root/'.env')
        self.assertEqual((self.root/'.env').read_bytes(),before)
        with self.assertRaises(ValueError):b.resolve({'MYSQL_MODE':'settings','DJANGO_ENV':'../dev'},self.root)

if __name__=='__main__':unittest.main()
