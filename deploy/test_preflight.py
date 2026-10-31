"""Verify cold-start waiting does not hide invalid object-storage credentials."""
import contextlib
import io
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0,str(Path(__file__).parent))
import deploy_check

class PreflightTests(unittest.TestCase):
    def check_storage(self,errors):
        mysql=SimpleNamespace(connect=MagicMock(),Error=RuntimeError)
        storage=MagicMock();storage.return_value.bucket_exists.side_effect=errors
        http=SimpleNamespace(PoolManager=MagicMock(),Timeout=MagicMock(),exceptions=SimpleNamespace(HTTPError=OSError))
        env={'MYSQL_HOST':'db.example.com','MYSQL_PORT':'3306','MYSQL_USER':'sample-user','MYSQL_PASSWORD':'sample-password','MYSQL_DATABASE':'sample-db','FILE_STORAGE_BACKEND':'minio','MINIO_STORAGE_ENDPOINT':'s3.example.com','MINIO_STORAGE_ACCESS_KEY':'sample-access','MINIO_STORAGE_SECRET_KEY':'sample-secret','MINIO_STORAGE_USE_HTTPS':'false','MINIO_STORAGE_MEDIA_BUCKET_NAME':'sample-bucket','MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET':'true'}
        with patch.dict(sys.modules,{'pymysql':mysql,'minio':SimpleNamespace(Minio=storage),'urllib3':http}),patch.dict(os.environ,env,clear=True),patch.object(deploy_check.time,'sleep') as sleep,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            result=deploy_check.check()
        return result,storage.return_value.bucket_exists.call_count,sleep.call_count

    def test_new_storage_waits_until_ready(self):
        self.assertEqual(self.check_storage([ConnectionRefusedError(),True]),(0,2,1))

    def test_invalid_credentials_stop_without_retry(self):
        self.assertEqual(self.check_storage([RuntimeError('sample denied')]),(1,1,0))

if __name__=='__main__':unittest.main()
