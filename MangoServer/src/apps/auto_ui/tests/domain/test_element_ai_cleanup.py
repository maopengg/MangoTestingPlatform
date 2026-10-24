from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from src.apps.auto_ui.models import Page, PageElement, UiElementHealRecord, UiElementSnapshot
from src.apps.auto_ui.services.element_ai.cleanup_service import ElementAiCleanupService
from src.apps.auto_ui.services.element_ai.element_ai_service import ElementAiService
from src.apps.task_center.services.scheduling.system_job import SystemJobService
from src.apps.test_center.models import ProductModule, Project, ProjectProduct

REPOSITORY_ROOT = Path(__file__).resolve().parents[6]


class ElementAiCleanupServiceTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='元素AI清理项目')
        product = ProjectProduct.objects.create(project=project, name='主服务')
        module = ProductModule.objects.create(project_product=product, name='智能模块', level=1)
        page = Page.objects.create(
            project_product=product,
            module=module,
            name='智能页面',
            url='https://example.test/',
        )
        self.element = PageElement.objects.create(
            page=page,
            name='输入框',
            exp=2,
            loc='locator("#input")',
        )
        self.page = page
        self.product = product

    def create_heal(self, status: int):
        return UiElementHealRecord.objects.create(
            element=self.element,
            page=self.page,
            project_product=self.product,
            test_env=2,
            status=status,
            page_url='https://example.test/',
        )

    def create_snapshot(self, status: int):
        sequence = UiElementSnapshot.objects.count() + 1
        return UiElementSnapshot.objects.create(
            element=self.element,
            page=self.page,
            project_product=self.product,
            test_env=2,
            status=status,
            url='https://example.test/',
            exp=2,
            loc=f'locator("#input-{sequence}")',
            html_hash=f'html-{sequence}',
            locator_hash=f'locator-{sequence}',
        )

    def test_cleanup_expires_and_caps_heal_records_and_snapshots(self):
        old_pending = self.create_heal(1)
        recent_pending = [self.create_heal(1) for _ in range(4)]
        old_resolved = self.create_heal(4)
        recent_resolved = [self.create_heal(4) for _ in range(5)]
        old_inactive_snapshot = self.create_snapshot(2)
        recent_inactive_snapshot = self.create_snapshot(2)
        recent_active_snapshots = [self.create_snapshot(1) for _ in range(4)]
        old_time = timezone.now() - timedelta(days=120)
        UiElementHealRecord.objects.filter(id__in=[old_pending.id, old_resolved.id]).update(
            create_time=old_time
        )
        UiElementSnapshot.objects.filter(id=old_inactive_snapshot.id).update(create_time=old_time)

        with patch.multiple(
                ElementAiCleanupService,
                PENDING_HEAL_KEEP_PER_SCOPE=2,
                RESOLVED_HEAL_KEEP_PER_SCOPE=3,
                ACTIVE_SNAPSHOT_KEEP_PER_SCOPE=2,
        ):
            result = ElementAiCleanupService.cleanup()

        self.assertEqual(result['expired_pending_heal_count'], 1)
        self.assertEqual(result['expired_resolved_heal_count'], 1)
        self.assertEqual(result['capped_pending_heal_count'], 2)
        self.assertEqual(result['capped_resolved_heal_count'], 2)
        self.assertEqual(result['inactive_snapshot_count'], 1)
        self.assertEqual(result['capped_active_snapshot_count'], 2)
        self.assertEqual(result['deleted_count'], 9)
        self.assertEqual(UiElementHealRecord.objects.filter(status=1).count(), 2)
        self.assertEqual(UiElementHealRecord.objects.filter(status=4).count(), 3)
        self.assertEqual(UiElementSnapshot.objects.filter(status=1).count(), 2)
        self.assertTrue(UiElementSnapshot.objects.filter(id=recent_inactive_snapshot.id).exists())
        self.assertEqual(
            set(UiElementHealRecord.objects.filter(status=1).values_list('id', flat=True)),
            {item.id for item in recent_pending[-2:]},
        )
        self.assertEqual(
            set(UiElementHealRecord.objects.filter(status=4).values_list('id', flat=True)),
            {item.id for item in recent_resolved[-3:]},
        )
        self.assertEqual(
            set(UiElementSnapshot.objects.filter(status=1).values_list('id', flat=True)),
            {item.id for item in recent_active_snapshots[-2:]},
        )

    def test_save_heal_record_caps_current_element_environment_immediately(self):
        with patch.object(ElementAiCleanupService, 'PENDING_HEAL_KEEP_PER_SCOPE', 2):
            for index in range(3):
                ElementAiService.save_heal_record({
                    'element': self.element.id,
                    'test_env': 2,
                    'status': 1,
                    'page_url': 'https://example.test/',
                    'failed_reason': f'失败-{index}',
                })

        records = UiElementHealRecord.objects.filter(
            element=self.element,
            test_env=2,
            status=1,
        ).order_by('-id')
        self.assertEqual(records.count(), 2)
        self.assertEqual(
            list(records.values_list('failed_reason', flat=True)),
            ['失败-2', '失败-1'],
        )

    def test_ai_info_splits_history_and_loads_full_snapshot_on_detail(self):
        snapshot = self.create_snapshot(1)
        UiElementSnapshot.objects.filter(id=snapshot.id).update(
            element_text='提交',
            element_attributes={'data-testid': 'submit'},
            outer_html='<button data-testid="submit">提交</button>',
            accessibility_digest={'nodes': [{'role': 'button', 'name': '提交'}]},
        )
        heal = self.create_heal(2)
        UiElementHealRecord.objects.filter(id=heal.id).update(
            candidates=[{'loc': 'get_by_role("button", name="提交")', 'verified': True}],
            ai_prompt_summary={'locator_engine': {'trace_id': 'trace-1'}},
            failed_loc='locator("#old-submit")',
            current_context={'page_title': '提交页'},
        )

        info = ElementAiService.ai_info(self.element.id, 2)
        self.assertNotIn('snapshots', info)
        self.assertNotIn('heal_records', info)
        self.assertNotIn('latest_snapshot', info)
        self.assertEqual(info['latest_heal_record']['id'], heal.id)
        self.assertEqual(len(info['latest_heal_record']['candidates']), 1)

        history = ElementAiService.snapshot_history(self.element.id, 2, 1, 10)
        self.assertEqual(history['count'], 1)
        self.assertEqual(history['pageSize'], 10)
        self.assertNotIn('outer_html', history['items'][0])

        detail = ElementAiService.snapshot_detail(snapshot.id, self.element.id)
        self.assertEqual(detail['element_attributes'], {'data-testid': 'submit'})
        self.assertIn('<button', detail['outer_html'])
        self.assertEqual(detail['accessibility_digest']['nodes'][0]['role'], 'button')

        heal_history = ElementAiService.heal_history(self.element.id, 2, 1, 20)
        self.assertEqual(heal_history['count'], 1)
        self.assertNotIn('candidates', heal_history['items'][0])

        heal_detail = ElementAiService.heal_record_detail(heal.id, self.element.id)
        self.assertEqual(heal_detail['failed_loc'], 'locator("#old-submit")')
        self.assertEqual(heal_detail['current_context']['page_title'], '提交页')
        self.assertEqual(len(heal_detail['candidates']), 1)


class ElementAiCleanupSystemJobTests(SimpleTestCase):
    def test_cleanup_job_is_registered_for_daily_execution(self):
        job = SystemJobService.get_job('clean_ui_element_ai_history')

        self.assertIsNotNone(job)
        self.assertEqual(job.cron, '50 2 * * *')
        self.assertEqual(job.handler.__name__, 'clean_ui_element_ai_history')

    def test_scheduler_runner_dispatches_cleanup_job(self):
        source = (
                REPOSITORY_ROOT / 'MangoServer/src/processes/scheduler/runner.py'
        ).read_text(encoding='utf-8')

        self.assertIn("('clean_ui_element_ai_history', '50 2 * * *'", source)
