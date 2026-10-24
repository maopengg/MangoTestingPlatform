import os
import subprocess
import sys

from django.test import SimpleTestCase


class DatabaseDeploymentConfigTests(SimpleTestCase):
    def test_container_connection_overrides_environment_defaults(self):
        environment = {
            **os.environ,
            'DJANGO_ENV': 'master',
            'MYSQL_DATABASE': 'deployment_test_database',
            'MYSQL_USER': 'deployment_test_app',
            'MYSQL_PASSWORD': 'deployment-test-only-password',
            'MYSQL_HOST': 'deployment-test-db',
            'MYSQL_PORT': '13306',
        }
        subprocess.run(
            [sys.executable, '-c', '''
from src.settings import DATABASES
config = DATABASES['default']
assert config['NAME'] == 'deployment_test_database'
assert config['USER'] == 'deployment_test_app'
assert config['PASSWORD'] == 'deployment-test-only-password'
assert config['HOST'] == 'deployment-test-db'
assert config['PORT'] == 13306
'''],
            env=environment,
            check=True,
            capture_output=True,
            timeout=30,
        )
