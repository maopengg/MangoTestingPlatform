import unittest

from src.services.ui.test_case import TestCase


class UiCaseEnvironmentScopeTests(unittest.TestCase):

    def test_ui_case_environment_scope_defaults_to_common(self):
        matches = TestCase._matches_test_environment

        self.assertTrue(matches({}, 1))
        self.assertTrue(matches({'test_envs': None}, 1))
        self.assertTrue(matches({'test_envs': []}, 1))
        self.assertTrue(matches({'test_envs': [1, 2]}, 1))
        self.assertFalse(matches({'test_envs': [2]}, 1))


if __name__ == '__main__':
    unittest.main()
