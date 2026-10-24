import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('bootstrap', Path(__file__).with_name('bootstrap.py'))
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class DeploymentCredentialsTest(unittest.TestCase):
    def test_redeploy_preserves_credentials_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env.deploy'
            first = bootstrap.initialize(path)
            second = bootstrap.initialize(path)
            self.assertEqual(first, second)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(first['MYSQL_PASSWORD'], first['MYSQL_ROOT_PASSWORD'])

    def test_invalid_existing_config_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env.deploy'
            path.write_text('MYSQL_PASSWORD=existing\n')
            with self.assertRaises(ValueError):
                bootstrap.initialize(path)
            self.assertEqual(path.read_text(), 'MYSQL_PASSWORD=existing\n')

    def test_invalid_port_does_not_write_config(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', WEB_PORT='0'):
            path = Path(directory) / '.env.deploy'
            with self.assertRaises(ValueError):
                bootstrap.initialize(path)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
