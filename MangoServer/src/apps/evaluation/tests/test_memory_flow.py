"""Run the real ORM flow in a separate process with an in-memory database."""
import os
from pathlib import Path
import subprocess
import sys
from django.test import SimpleTestCase


class EvaluationMemoryFlowTests(SimpleTestCase):
    def test_full_case_flow_in_isolated_memory_database(self):
        project = Path(__file__).resolve().parents[4]
        environment = {**os.environ, "PYTHONPATH": str(project)}
        result = subprocess.run([sys.executable, "-m", "src.apps.evaluation.tests.memory_flow"],
                                cwd=project, env=environment, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MEMORY_FLOW_OK", result.stdout)
