from django.db.models import Q
from mangotools.enums import TaskEnum

from src.apps.test_center.models import TestSuiteDetails


class ReportNoticeSelector:
    @staticmethod
    def failed_details(suite_ids):
        return list(TestSuiteDetails.objects.filter(test_suite_id__in=suite_ids, is_excluded=False).filter(
            Q(status__in=(TaskEnum.FAIL.value, TaskEnum.STOPPED.value)) | Q(fail__gt=0),
        ).only('id', 'test_suite_id', 'case_id', 'case_name', 'type', 'status', 'fail',
               'summary_data', 'error_message').order_by('test_suite_id', 'create_time', 'id'))
