"""Isolated SQLite smoke test. Never connects to or migrates a configured database."""


def main():
    import os
    os.environ["DJANGO_ENV"] = "dev"
    os.environ["DJANGO_SETTINGS_MODULE"] = "src.settings"
    from django.conf import settings
    settings.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
    import django
    django.setup()
    from django.db import connection, models
    from django.utils import timezone
    from unittest.mock import patch
    from src.apps.evaluation.models import EvaluationDataset, EvaluationDatasetVersion, EvaluationDatasetItem, EvaluationCase, EvaluationCaseExecution, EvaluationItemResult, EvaluationGradeResult
    from src.apps.test_center.models import ProjectProduct, ProductModule, TestSuite, TestSuiteDetails
    from src.apps.user.models import User
    from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService
    from src.apps.evaluation.services.dataset.dataset_version import EvaluationDatasetVersionService
    from src.apps.evaluation.services.dataset.dataset_item import EvaluationDatasetItemService
    from src.apps.evaluation.services.assets.case import EvaluationCaseService
    from src.apps.evaluation.services.execution.execution import EvaluationCaseExecutionService
    from src.apps.evaluation.exceptions import EvaluationError
    from src.apps.system.services.configuration.system_config import SystemConfigService
    from src.apps.auto_api.models import ApiInfo, ApiInfoRevision, ApiInfoRelease
    SystemConfigService._environment_display_names_cache = (float("inf"), {})
    assert connection.vendor == "sqlite" and connection.settings_dict["NAME"] == ":memory:"
    with connection.schema_editor() as editor:
        for model in (User, ProjectProduct, ProductModule, TestSuite, TestSuiteDetails, ApiInfo, ApiInfoRevision, ApiInfoRelease, EvaluationDataset, EvaluationDatasetVersion, EvaluationDatasetItem, EvaluationCase, EvaluationCaseExecution, EvaluationItemResult, EvaluationGradeResult):
            editor.create_model(model)
    def seed(model, pk):
        values = {"id": pk}
        for field in model._meta.concrete_fields:
            if field.primary_key or field.null or field.has_default() or getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue
            if field.is_relation:
                values[field.attname] = 1
            elif isinstance(field, (models.DateField, models.DateTimeField)):
                values[field.attname] = timezone.now()
            elif isinstance(field, models.BooleanField):
                values[field.attname] = False
            elif isinstance(field, (models.IntegerField, models.FloatField, models.DecimalField)):
                values[field.attname] = 1
            else:
                values[field.attname] = "example"
        instance = model(**values)
        model.objects.bulk_create([instance])
        return instance
    import itertools
    with connection.constraint_checks_disabled(), patch("src.apps.evaluation.selectors.scope.PermissionMenuService.is_effective_super_admin", return_value=True), patch("src.common.utils.snowflake.Snowflake.generate_id", side_effect=itertools.count(10000)):
        user = seed(User, 1)
        product = seed(ProjectProduct, 1)
        module = seed(ProductModule, 1)
        dataset = EvaluationDataset.objects.create(name="memory smoke", task_type=["generation"])
        version = EvaluationDatasetVersionService.create(dataset_id=dataset.id, values={"schema_snapshot": {}}, user=user)
        first = EvaluationDatasetItemService.save(version=version, values={"input_data": {"question": "负责人是谁？"}, "expected_output": {"answer": "张三"}})
        second = EvaluationDatasetItemService.save(version=version, values={"input_data": {"question": "负责人是谁"}, "expected_output": {"answer": "张三"},
            "grading_config": {"mode": "replace", "graders": [{"grader_key": "contains", "metric_key": "contains", "parameters": {"expected_path": "answer", "actual_path": "answer"}}]}})
        EvaluationVersionService.publish_dataset_version(version.id, user)
        version.refresh_from_db()
        config = {"schema_version": 1, "target": {"type": "script", "parameters": {"code": 'def main(input, context):\n    return {"answer": "张三"}\n'}},
            "grading": {"default_graders": [{"grader_key": "exact_match", "metric_key": "accuracy"}]}, "execution": {"repeat_count": 2}}
        case = EvaluationCaseService.save(values={"name": "smoke Case", "project_product": product, "dataset_version": version, "status": "enabled", "config": config})
        from src.apps.evaluation.selectors.target import interface_choices
        published_api, unpublished_api, unsupported_api = [seed(ApiInfo, pk) for pk in (1, 2, 3)]
        ApiInfo.objects.filter(pk=3).update(protocol_type="grpc")
        revision = seed(ApiInfoRevision, 1)
        release = seed(ApiInfoRelease, 1)
        ApiInfoRelease.objects.filter(pk=release.pk).update(is_current=True, status="published", revision=revision)
        choices = interface_choices(case.id, user, module_id=module.id)
        assert [row["id"] for row in choices["items"]] == [published_api.id, unpublished_api.id]
        assert [row["published"] for row in choices["items"]] == [True, False]
        interface_config = {**config, "target": {"type": "api_info", "ref_id": published_api.id}}
        normalized = EvaluationCaseService.normalize({"config": interface_config}, case)
        assert normalized["config"]["target"]["version_ref"] == {"kind": "api_info_release", "id": release.id}
        original = EvaluationCaseExecutionService.create({"case_id": case.id, "test_env": 1, "idempotency_key": "first"}, user)
        assert original.item_results.count() == 4
        assert EvaluationCaseExecutionService.create({"case_id": case.id, "test_env": 1, "idempotency_key": "first"}, user).pk == original.pk
        try:
            EvaluationCaseExecutionService.create({"case_id": case.id, "test_env": 1, "item_ids": [first.id], "idempotency_key": "first"}, user)
        except EvaluationError:
            pass
        else:
            raise AssertionError("Different payload reused an idempotency key")
        EvaluationCaseExecutionService.execute(original.id)
        original.refresh_from_db()
        assert original.status == "completed" and original.verdict == "passed", (original.status, original.summary, original.details)
        assert original.summary["total"] == 4 and original.summary["valid"] == 4 and original.summary["item_count"] == 2
        assert original.summary["metrics"]["accuracy"]["total"] == 2
        assert original.summary["metrics"]["contains"]["total"] == 2
        EvaluationCase.objects.filter(pk=case.pk).update(config={**case.config, "assessment": {"objective": "旧目标"}})
        case = EvaluationCaseService.save(instance=case, values={"description": "新的场景描述"})
        case.refresh_from_db()
        assert case.description == "新的场景描述" and "assessment" not in case.config
        report = TestSuiteDetails.objects.get(pk=original.report_detail_id)
        assert report.type == 4 and report.status == 1 and report.success == 4
        assert report.summary_data["children"]["dataset"]["version_id"] == version.id
        assert TestSuite.objects.get(pk=report.test_suite_id).status == 1
        from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
        assert TestSuiteSummaryService.summary_data(report.test_suite_id)["evaluation_count"] == 4
        assert TestSuite.objects.count() == 1, "Idempotent replay created a duplicate report"
        assert set(EvaluationGradeResult.objects.filter(item_result__execution=original).values_list("grader_key", flat=True)) == {"exact_match", "contains"}
        assert all(row.attempts and row.grade_status == "graded" for row in original.item_results.all())
        import json
        for index, value in enumerate(("北京", False, 0, "", [], None)):
            scalar_config = {
                "target": {"type": "script", "parameters": {"code": 'def main(input, context):\n    return {"value": ' + repr(value) + '}\n'}},
                "mapping": {"output": {"paths": ["$.value"]}},
                "grading": {"default_graders": [{"grader_key": "json_schema", "metric_key": "value", "parameters": {"schema": {}}}]},
            }
            scalar_case = EvaluationCaseService.save(values={"name": f"scalar-{index}", "project_product": product, "dataset_version": version, "status": "enabled", "config": scalar_config})
            scalar_run = EvaluationCaseExecutionService.create({"case_id": scalar_case.id, "test_env": 1, "item_ids": [first.id]}, user)
            EvaluationCaseExecutionService.execute(scalar_run.id)
            row = scalar_run.item_results.get()
            assert json.dumps(row.actual_output) == json.dumps(value), (value, row.actual_output, row.error_message)
            assert json.dumps(row.attempts[-1]["output_snapshot"]) == json.dumps(value)
            if value is None:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT json_type(actual_output) FROM evaluation_item_result WHERE id = %s', [row.id])
                    assert cursor.fetchone()[0] == 'null'
        config["target"]["parameters"]["code"] = 'def main(input, context):\n    return {"answer": "李四"}\n'
        case = EvaluationCaseService.save(values={"config": config}, instance=case)
        failed = EvaluationCaseExecutionService.create({"case_id": case.id, "test_env": 1}, user)
        EvaluationCaseExecutionService.execute(failed.id)
        failed.refresh_from_db()
        assert failed.verdict == "failed"
        config["target"]["parameters"]["code"] = 'def main(input, context):\n    return {"answer": "张三"}\n'
        EvaluationCaseService.save(values={"config": config}, instance=case)
        retry = EvaluationCaseExecutionService.retry_failed(failed.id, user, "retry-key")
        assert '李四' in retry.snapshot["target"]["parameters"]["code"]
        EvaluationCaseExecutionService.execute(retry.id)
        retry.refresh_from_db()
        assert retry.verdict == "failed" and retry.retry_of_id == failed.id
        pending = EvaluationCaseExecutionService.create({"case_id": case.id, "test_env": 1}, user)
        EvaluationCaseExecutionService.stop(pending.id)
        EvaluationCaseExecutionService.execute(pending.id)
        pending.refresh_from_db()
        assert pending.status == "stopped"
        assert all(row.execution_status == "cancelled" and not row.attempts for row in pending.item_results.all())
        config["grading"]["required_graders"] = [{"grader_key": "json_schema", "metric_key": "structure", "hard_gate": True, "weight": 0, "parameters": {"schema": {"type": "object", "required": ["absent_field"]}}}]
        config["execution"] = {"repeat_count": 1, "stop_on_critical_failure": True}
        case = EvaluationCaseService.save(values={"config": config}, instance=case)
        critical = EvaluationCaseExecutionService.create({"case_id": case.id, "test_env": 1}, user)
        EvaluationCaseExecutionService.execute(critical.id)
        critical.refresh_from_db()
        assert critical.status == "completed" and critical.verdict == "failed"
        assert not critical.item_results.filter(execution_status="pending").exists()
        cancelled = critical.item_results.get(dataset_item_id=second.id)
        assert cancelled.execution_status == "cancelled" and cancelled.error_category == "critical_gate_stopped"
        assert not cancelled.attempts

        from src.apps.evaluation.presenters import execution_record, result_record, case_record
        from src.apps.evaluation.services.assets.assets import create_case, update_case, set_case_status, ensure_dataset
        from src.apps.evaluation.selectors.assets import datasets, get_dataset
        assert execution_record(original)["status"] == "completed"
        projection = result_record(original.item_results.prefetch_related("grade_results").first())
        assert projection["grades"] and projection["actual_output"] and projection["attempts"]
        created = create_case({"name": "MCP asset flow", "project_product_id": product.id, "dataset_version_id": version.id, "config": config}, user)
        assert case_record(created)["status"] == "draft"
        created = set_case_status(created.id, "enabled", user)
        assert created.status == "enabled"
        updated = update_case(created.id, {"config": config}, user)
        assert updated.status == "enabled" and updated.dataset_version_id == version.id
        reused, was_created = ensure_dataset({"name": dataset.name, "task_type": ["generation"]}, user)
        assert reused.id == dataset.id and not was_created and EvaluationDataset.objects.count() == 1
        assert datasets(None).count() == 0
        with patch("src.apps.evaluation.selectors.scope.PermissionMenuService.is_effective_super_admin", return_value=False), \
             patch("src.apps.evaluation.selectors.scope.ProjectProductScopeService.can_view_all_project_data", return_value=False), \
             patch("src.apps.evaluation.selectors.scope.ProjectProductScopeService.project_product_ids_for_user", return_value=[]), \
             patch("src.apps.evaluation.selectors.scope.PermissionMenuService.permission_keys_for_user", return_value=set()):
            assert datasets(user).count() == 0
            try:
                get_dataset(dataset.id, user)
            except EvaluationError:
                pass
            else:
                raise AssertionError("MCP asset selector exposed an out-of-scope dataset")
        from src.apps.system.services.ai.evaluation_profiles import EvaluationAiProfileService
        profiles = EvaluationAiProfileService.parse([
            {"id": name, "name": name, "base_url": "https://example.com/v1", "api_key": "test-only-key", "model": name}
            for name in ("answer", "judge", "summary")
        ])
        calls = []
        def ai_chat(**kwargs):
            name = kwargs["config"].model
            calls.append(name)
            output = {"answer": "张三"} if name == "answer" else (
                {"score": 100.0, "passed": True, "confidence": 0.99, "requires_review": False, "reason": "正确", "evidence": {"quote": "张三"}}
                if name == "judge" else {"overview": "两条样本有效", "findings": [], "recommendations": []})
            return {"choices": [{"message": {"content": output}}]}
        ai_config = {
            "ai": {"judge_profile_id": "judge", "answer_profile_id": "answer", "summary_profile_id": "summary"},
            "target": {"type": "script", "parameters": {"code": 'def main(input, context):\n    return {"top_items": [{"content": "负责人是张三"}]}\n'}},
            "answering": {"question_path": "question"},
            "grading": {"required_graders": [{"grader_key": "model_judge", "metric_key": "quality"}],
                        "default_graders": [{"grader_key": "exact_match", "metric_key": "answer", "parameters": {"expected_path": "answer", "actual_path": "answer"}}]},
        }
        ai_case = EvaluationCaseService.save(values={"name": "独立 AI 验证", "project_product": product,
            "dataset_version": version, "config": ai_config, "status": "enabled"})
        with patch.object(EvaluationAiProfileService, "profiles", return_value=profiles), \
             patch("src.apps.evaluation.services.model.ai.AiService.load_config", side_effect=AssertionError("Default AI must not be read")), \
             patch("src.apps.evaluation.services.model.ai.AiService.json_chat", side_effect=ai_chat):
            ai_execution = EvaluationCaseExecutionService.create({"case_id": ai_case.id, "test_env": 1}, user)
            EvaluationCaseExecutionService.execute(ai_execution.id)
            ai_execution.refresh_from_db()
            assert ai_execution.summary["valid"] == 2 and ai_execution.verdict == "passed"
            assert ai_execution.summary["ai_summary"]["status"] == "completed"
            assert set(calls) == {"answer", "judge", "summary"}, calls
            summary_report = TestSuiteDetails.objects.get(pk=ai_execution.report_detail_id)
            assert summary_report.summary_data["children"]["summary"]["ai_summary"]["model"]["profile_id"] == "summary"
            with patch("src.apps.evaluation.services.reporting.summary.json_chat", side_effect=ConnectionError("summary endpoint unavailable")):
                EvaluationCaseExecutionService.aggregate(ai_execution)
            assert ai_execution.verdict == "passed" and ai_execution.summary["ai_summary"]["status"] == "failed"
        from src.apps.evaluation.tests.workflow_flow import verify_workflow_flow
        verify_workflow_flow(user, product)
        from src.apps.evaluation.tests.item_source_flow import verify_item_source_flow
        verify_item_source_flow(user, product)
        print("MEMORY_FLOW_OK: publish, item override, frozen execution, independent answer/judge/summary AI, summary failure isolation, frozen retry and scoped MCP assets; WORKFLOW_FLOW_OK; ITEM_SOURCE_FLOW_OK")


if __name__ == "__main__":
    main()
