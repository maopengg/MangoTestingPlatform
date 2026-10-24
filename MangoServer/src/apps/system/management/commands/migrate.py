from django.core.management.base import CommandError
from django.core.management.commands.migrate import Command as DjangoMigrateCommand
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder

TEST_CENTER_BASELINES = (
    ("test_center", "0001_initial"),
    ("test_center", "0002_execution_models_state"),
)
RELOCATED_TABLES = {
    "execution_result",
    "file_data",
    "notice_group",
    "product_module",
    "project",
    "project_product",
    "test_object",
    "test_suite",
    "test_suite_details",
}
ALREADY_APPLIED_RELOCATION_MIGRATIONS = {
    ("auto_ai", "0006_alter_aimcpserver_module_and_more"),
    ("auto_api", "0041_alter_apiauthconfig_notice_group_and_more"),
    ("auto_pytest", "0017_alter_pytestcase_module_and_more"),
    ("auto_ui", "0029_alter_page_module_alter_page_project_product_and_more"),
    ("auto_user", "0009_alter_departmentprojectproductpermission_project_product"),
    ("functional_test", "0014_alter_functionaltestcontextresource_file_and_more"),
    ("gray_config", "0006_alter_grayexecutionlog_database_and_more"),
    ("monitoring", "0006_alter_monitoringtask_notice_group_and_more"),
    ("task_center", "0011_alter_scheduledtaskgroupexecution_notice_group_and_more"),
    ("auto_system", "0049_delete_executortask_delete_filedata_and_more"),
}


class Command(DjangoMigrateCommand):
    """Run Django migrations with a one-time test_center state bootstrap."""

    def _record_existing_test_center_baseline(self, database: str) -> None:
        connection = connections[database]
        recorder = MigrationRecorder(connection)
        applied = set(recorder.applied_migrations())
        missing_baselines = [baseline for baseline in TEST_CENTER_BASELINES if baseline not in applied]
        if not missing_baselines:
            return
        if not (applied & ALREADY_APPLIED_RELOCATION_MIGRATIONS):
            return

        existing_tables = set(connection.introspection.table_names())
        missing_tables = sorted(RELOCATED_TABLES - existing_tables)
        if missing_tables:
            raise CommandError(
                "检测到 test_center 历史迁移已执行，但迁移基线尚未登记，且以下历史表缺失："
                + ", ".join(missing_tables)
            )

        for baseline in missing_baselines:
            recorder.record_applied(*baseline)
        self.stdout.write(
            self.style.SUCCESS(
                "已为现有数据库登记 test_center 状态基线；未创建、删除或修改业务表。"
            )
        )

    def handle(self, *args, **options):
        self._record_existing_test_center_baseline(options["database"])
        return super().handle(*args, **options)
