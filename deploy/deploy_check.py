"""Deployment preflight: no DDL, migration or writes; never print credentials."""
import os
import sys
import time


def check():
    import pymysql
    for attempt in range(12):
        try:
            connection = pymysql.connect(host=os.environ['MYSQL_HOST'], port=int(os.environ['MYSQL_PORT']),
                user=os.environ['MYSQL_USER'], password=os.environ['MYSQL_PASSWORD'],
                database=os.environ['MYSQL_DATABASE'], connect_timeout=5, read_timeout=5, write_timeout=5)
            with connection:
                with connection.cursor() as cursor: cursor.execute('SELECT 1')
            break
        except pymysql.Error as error:
            if attempt < 11 and error.args[0] in {2002,2003,2013}:
                time.sleep(2)
                continue
            print('MySQL 连接失败（错误码 %s），请检查 .env 的 MYSQL_HOST/PORT/DATABASE/USER/PASSWORD 及用户来源授权。' % error.args[0], file=sys.stderr)
            return 1
    print('MySQL 连接验证通过。')
    if os.environ.get('FILE_STORAGE_BACKEND') in {'minio','tos'}:
        from minio import Minio
        import urllib3
        env=os.environ
        client=Minio(env['MINIO_STORAGE_ENDPOINT'], access_key=env['MINIO_STORAGE_ACCESS_KEY'],
                     secret_key=env['MINIO_STORAGE_SECRET_KEY'], secure=env['MINIO_STORAGE_USE_HTTPS']=='true',
                     region=env.get('MINIO_STORAGE_REGION') or None,
                     http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=5,read=10),retries=False))
        if env.get('MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE')=='true': client.enable_virtual_style_endpoint()
        for attempt in range(12):
            try:
                exists=client.bucket_exists(env['MINIO_STORAGE_MEDIA_BUCKET_NAME'])
                if not exists and env['MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET']!='true':
                    print('对象存储桶不存在，请预先创建或启用 S3_AUTO_CREATE_BUCKET。',file=sys.stderr)
                    return 1
                break
            except Exception as error:
                # Newly started internal storage may not accept requests immediately.
                transient=isinstance(error,(urllib3.exceptions.HTTPError,OSError)) or getattr(error,'code',None) in {'XMinioServerNotInitialized','ServiceUnavailable','SlowDown'}
                if transient and attempt < 11:
                    time.sleep(2)
                    continue
                print('对象存储验证失败，请检查 S3_ENDPOINT/REGION/BUCKET/ACCESS_KEY/SECRET_KEY、HTTPS 与桶访问权限。',file=sys.stderr)
                return 1
        print('对象存储验证通过（未写入文件）。')
    return 0


if __name__=='__main__': sys.exit(check())
