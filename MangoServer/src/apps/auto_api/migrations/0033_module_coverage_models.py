import django.db.models.deletion
from django.db import migrations, models

TABLES = (
    ("functional_test_module_coverage_scan", "api_module_coverage_scan"),
    ("functional_test_module_coverage_case", "api_module_coverage_case"),
    ("functional_test_module_coverage_case_snapshot", "api_module_coverage_case_snapshot"),
    ("functional_test_module_coverage_interface_snapshot", "api_module_coverage_interface_snapshot"),
)


def rename_tables(apps, schema_editor):
    for old_name, new_name in TABLES:
        schema_editor.alter_db_table(None, old_name, new_name)


def restore_table_names(apps, schema_editor):
    for old_name, new_name in reversed(TABLES):
        schema_editor.alter_db_table(None, new_name, old_name)


class Migration(migrations.Migration):
    dependencies = [
        ("auto_api", "0032_alter_apicase_scenario_layer_and_more"),
        ("functional_test", "0012_remove_module_coverage_model_state"),
        ("auto_system", "0043_remove_tasks_test_env_remove_tasks_timing_strategy_and_more"),
        ("auto_user", "0007_department_update_user_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(rename_tables, restore_table_names)],
            state_operations=[
                migrations.CreateModel(
                    name="ModuleCoverageScan",
                    fields=[
                        ("id",
                         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                        ("update_time", models.DateTimeField(auto_now=True, verbose_name="修改时间")),
                        ("include_descendants", models.BooleanField(default=False, verbose_name="包含子模块")),
                        ("repository_key", models.CharField(max_length=256, verbose_name="仓库标识")),
                        ("repository_name", models.CharField(max_length=256, verbose_name="仓库名称")),
                        ("branch", models.CharField(max_length=256, verbose_name="分支")),
                        ("commit_sha", models.CharField(max_length=64, verbose_name="提交版本")),
                        ("base_commit_sha",
                         models.CharField(blank=True, max_length=64, null=True, verbose_name="增量基线提交")),
                        ("test_env", models.SmallIntegerField(blank=True, null=True, verbose_name="被测环境")),
                        ("scan_mode",
                         models.CharField(choices=[("full", "完整扫描"), ("incremental", "增量扫描")], default="full",
                                          max_length=16, verbose_name="扫描模式")),
                        ("expected_case_count", models.PositiveIntegerField(verbose_name="预期Case数")),
                        ("expected_interface_count", models.PositiveIntegerField(default=0, verbose_name="预期接口数")),
                        ("idempotency_key", models.CharField(max_length=128, unique=True, verbose_name="幂等键")),
                        ("status", models.CharField(
                            choices=[("uploading", "上传中"), ("completed", "已完成"), ("cancelled", "已取消")],
                            db_index=True, default="uploading", max_length=16, verbose_name="扫描状态")),
                        ("summary", models.JSONField(default=dict, verbose_name="扫描汇总")),
                        ("skill_name", models.CharField(default="mango-code-driven-api-case-builder", max_length=128)),
                        ("skill_version", models.CharField(default="1", max_length=64)),
                        ("schema_version", models.PositiveIntegerField(default=3)),
                        ("started_at", models.DateTimeField(blank=True, null=True)),
                        ("finished_at", models.DateTimeField(blank=True, null=True)),
                        ("created_by",
                         models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           related_name="created_module_coverage_scans", to="auto_user.user")),
                        ("module", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                     to="auto_system.productmodule")),
                        ("project_product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                              to="auto_system.projectproduct")),
                    ],
                    options={"db_table": "api_module_coverage_scan", "ordering": ["-id"]},
                ),
                migrations.CreateModel(
                    name="ModuleCoverageCase",
                    fields=[
                        ("id",
                         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                        ("update_time", models.DateTimeField(auto_now=True, verbose_name="修改时间")),
                        ("repository_key", models.CharField(max_length=256, verbose_name="仓库标识")),
                        ("branch", models.CharField(max_length=256, verbose_name="分支")),
                        ("source_key", models.CharField(max_length=512, verbose_name="稳定来源Key")),
                        ("source_key_hash",
                         models.CharField(editable=False, max_length=64, verbose_name="稳定来源Key哈希")),
                        ("interface_source_key",
                         models.CharField(default="", max_length=512, verbose_name="接口稳定来源Key")),
                        ("interface_source_key_hash", models.CharField(default="", editable=False, max_length=64,
                                                                       verbose_name="接口稳定来源Key哈希")),
                        ("case_no", models.CharField(max_length=128, verbose_name="Case编号")),
                        ("name", models.CharField(max_length=512, verbose_name="Case标题")),
                        ("interface_name", models.CharField(max_length=512, verbose_name="接口名称")),
                        ("method", models.CharField(max_length=16, verbose_name="请求方法")),
                        ("url", models.CharField(max_length=1024, verbose_name="接口URL")),
                        ("test_ownership",
                         models.CharField(default="HTTP API自动化", max_length=64, verbose_name="测试归属")),
                        ("status", models.CharField(
                            choices=[("pending_create", "待创建"), ("completed", "已完成"), ("deferred", "暂不处理"),
                                     ("removed", "已移除")], db_index=True, default="pending_create", max_length=32,
                            verbose_name="当前状态")),
                        ("execution_result", models.CharField(
                            choices=[("passed", "执行通过"), ("failed", "执行失败"), ("partial", "部分通过"),
                                     ("not_applicable", "不适用"), ("not_executed", "未执行")], default="not_executed",
                            max_length=32, verbose_name="执行结果")),
                        ("removed_at", models.DateTimeField(blank=True, null=True)),
                        ("api_case",
                         models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           related_name="module_coverage_cases", to="auto_api.apicase")),
                        ("api_case_revision",
                         models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           related_name="module_coverage_cases", to="auto_api.apicaserevision")),
                        ("first_seen_scan",
                         models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="first_seen_cases",
                                           to="auto_api.modulecoveragescan")),
                        ("last_seen_scan",
                         models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="last_seen_cases",
                                           to="auto_api.modulecoveragescan")),
                        ("module", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                     to="auto_system.productmodule")), ("project_product",
                                                                                        models.ForeignKey(
                                                                                            on_delete=django.db.models.deletion.PROTECT,
                                                                                            to="auto_system.projectproduct")),
                    ], options={"db_table": "api_module_coverage_case", "ordering": ["-id"]},
                ),
                migrations.CreateModel(
                    name="ModuleCoverageCaseSnapshot",
                    fields=[
                        ("id",
                         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                        ("content_hash", models.CharField(db_index=True, max_length=64, verbose_name="规范内容哈希")),
                        ("submitted_hash", models.CharField(max_length=64, verbose_name="上传内容哈希")),
                        ("payload", models.JSONField(default=dict, verbose_name="Case台账与覆盖路径快照")),
                        ("sync_action",
                         models.CharField(choices=[("created", "新增"), ("updated", "修改"), ("unchanged", "未变化")],
                                          max_length=16)), ("message", models.TextField(blank=True, null=True)),
                        ("api_case",
                         models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           related_name="module_coverage_snapshots", to="auto_api.apicase")),
                        ("api_case_revision",
                         models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           related_name="module_coverage_snapshots", to="auto_api.apicaserevision")),
                        ("coverage_case",
                         models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="snapshots",
                                           to="auto_api.modulecoveragecase")), ("scan", models.ForeignKey(
                            on_delete=django.db.models.deletion.PROTECT, related_name="case_snapshots",
                            to="auto_api.modulecoveragescan")),
                    ], options={"db_table": "api_module_coverage_case_snapshot", "ordering": ["id"]},
                ),
                migrations.AddField(model_name="modulecoveragecase", name="current_snapshot",
                                    field=models.ForeignKey(blank=True, null=True,
                                                            on_delete=django.db.models.deletion.SET_NULL,
                                                            related_name="current_for_cases",
                                                            to="auto_api.modulecoveragecasesnapshot")),
                migrations.CreateModel(
                    name="ModuleCoverageInterfaceSnapshot",
                    fields=[
                        ("id",
                         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                        ("repository_key", models.CharField(max_length=256, verbose_name="仓库标识")),
                        ("branch", models.CharField(max_length=256, verbose_name="分支")),
                        ("source_key", models.CharField(max_length=512, verbose_name="接口稳定来源Key")),
                        ("source_key_hash",
                         models.CharField(editable=False, max_length=64, verbose_name="接口稳定来源Key哈希")),
                        ("interface_name", models.CharField(max_length=512, verbose_name="接口名称")),
                        ("method", models.CharField(max_length=16, verbose_name="请求方法")),
                        ("url", models.CharField(max_length=1024, verbose_name="接口URL")),
                        ("mermaid", models.TextField(verbose_name="接口调用流程")),
                        ("node_ids", models.JSONField(default=list, verbose_name="流程节点ID")),
                        ("branch_ids", models.JSONField(default=list, verbose_name="流程分支ID")),
                        ("content_hash", models.CharField(db_index=True, max_length=64, verbose_name="规范内容哈希")),
                        ("submitted_hash", models.CharField(max_length=64, verbose_name="上传内容哈希")),
                        ("sync_action",
                         models.CharField(choices=[("created", "新增"), ("updated", "修改"), ("unchanged", "未变化")],
                                          max_length=16)), ("is_current",
                                                            models.BooleanField(db_index=True, default=False,
                                                                                verbose_name="是否当前接口快照")),
                        ("removed_at", models.DateTimeField(blank=True, null=True)),
                        ("module", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                     to="auto_system.productmodule")), ("project_product",
                                                                                        models.ForeignKey(
                                                                                            on_delete=django.db.models.deletion.PROTECT,
                                                                                            to="auto_system.projectproduct")),
                        ("scan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                   related_name="interface_snapshots",
                                                   to="auto_api.modulecoveragescan")),
                    ], options={"db_table": "api_module_coverage_interface_snapshot", "ordering": ["id"]},
                ),
                migrations.AddIndex(model_name="modulecoveragescan", index=models.Index(
                    fields=["project_product", "module", "repository_key", "branch", "status"],
                    name="ft_coverage_scan_scope_idx")),
                migrations.AddConstraint(model_name="modulecoveragecase", constraint=models.UniqueConstraint(
                    fields=("project_product", "module", "repository_key", "branch", "source_key_hash"),
                    name="ft_coverage_case_source_unique")),
                migrations.AddIndex(model_name="modulecoveragecase",
                                    index=models.Index(fields=["project_product", "module", "status", "-id"],
                                                       name="ft_coverage_case_state_idx")),
                migrations.AddConstraint(model_name="modulecoveragecasesnapshot",
                                         constraint=models.UniqueConstraint(fields=("scan", "coverage_case"),
                                                                            name="ft_coverage_scan_case_unique")),
                migrations.AddConstraint(model_name="modulecoverageinterfacesnapshot",
                                         constraint=models.UniqueConstraint(
                                             fields=("scan", "module", "source_key_hash"),
                                             name="ft_coverage_scan_interface_unique")),
                migrations.AddIndex(model_name="modulecoverageinterfacesnapshot", index=models.Index(
                    fields=["project_product", "module", "repository_key", "branch", "source_key_hash", "-id"],
                    name="ft_cov_interface_scope_idx")),
            ],
        ),
    ]
