import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('http_deployment',Path(__file__).parent.parent/'MangoServer/src/settings/deployment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class HttpDeploymentTests(unittest.TestCase):
    def test_development_defaults_unchanged(self):
        value={'CORS_ORIGIN_ALLOW_ALL':True}
        with patch.dict(os.environ,{},clear=True):m.apply_http_environment(value)
        self.assertEqual(value,{'CORS_ORIGIN_ALLOW_ALL':True})

    def test_deployed_origins_are_explicit(self):
        value={'CORS_ORIGIN_ALLOW_ALL':True}
        with patch.dict(os.environ,{'CORS_ALLOWED_ORIGINS':'https://web.example.com,http://web.example.com:8001'},clear=True):
            m.apply_http_environment(value)
        self.assertFalse(value['CORS_ORIGIN_ALLOW_ALL'])
        self.assertFalse(value['CORS_ALLOW_ALL_ORIGINS'])
        self.assertEqual(value['CORS_ALLOWED_ORIGINS'],value['CSRF_TRUSTED_ORIGINS'])
        self.assertIn('web.example.com:8001',value['MCP_ALLOWED_HOSTS'])
        self.assertEqual(value['MCP_ALLOWED_ORIGINS'],value['CORS_ALLOWED_ORIGINS'])

    def test_invalid_origins_rejected(self):
        for origin in ['*','https://web.example.com/api','https://user:password@web.example.com']:
            with self.subTest(origin=origin),patch.dict(os.environ,{'CORS_ALLOWED_ORIGINS':origin},clear=True),self.assertRaises(ValueError):
                m.apply_http_environment({})
