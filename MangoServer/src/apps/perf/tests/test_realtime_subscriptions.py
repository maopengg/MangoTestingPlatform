from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from src.apps.perf.services.reporting.realtime import PerfRealtimeService


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class PerfRealtimeSubscriptionTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch('src.apps.perf.services.reporting.realtime.time', return_value=100)
    def test_subscribe_refresh_and_expiration(self, now):
        PerfRealtimeService.subscribe('run', 1, 7)
        PerfRealtimeService.subscribe('run', 1, 8)
        self.assertEqual(set(PerfRealtimeService.viewers('run', 1)), {7, 8})
        now.return_value = 130
        PerfRealtimeService.subscribe('run', 1, 7)
        now.return_value = 160
        self.assertEqual(PerfRealtimeService.viewers('run', 1), [7])
        now.return_value = 190
        self.assertEqual(PerfRealtimeService.viewers('run', 1), [])

    @patch('src.apps.perf.services.reporting.realtime.time', return_value=100)
    def test_unsubscribe_is_idempotent_and_scopes_stay_isolated(self, now):
        PerfRealtimeService.subscribe('run', 1, 7)
        PerfRealtimeService.subscribe('run', 1, 8)
        PerfRealtimeService.subscribe('run', 2, 7)
        PerfRealtimeService.unsubscribe('run', 1, 7)
        PerfRealtimeService.unsubscribe('run', 1, 7)
        self.assertEqual(PerfRealtimeService.viewers('run', 1), [8])
        self.assertEqual(PerfRealtimeService.viewers('run', 2), [7])
        self.assertEqual(PerfRealtimeService.viewers('run', 3), [])
