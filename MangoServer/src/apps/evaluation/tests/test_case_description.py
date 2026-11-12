from copy import deepcopy
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.evaluation.api.serializers.case import CaseSerializer
from src.apps.evaluation.formatters.case_description import case_description, scenario_description
from src.apps.evaluation.models import EvaluationCase, EvaluationDataset, EvaluationDatasetVersion
from src.apps.evaluation.presenters import case_record, case_summary
from src.apps.evaluation.services.assets.case import EvaluationCaseService
from src.apps.evaluation.tests.test_case_flow import case_config
from src.apps.test_center.models import ProjectProduct


class CaseDescriptionTests(SimpleTestCase):
    def case(self):
        product = ProjectProduct(pk=5)
        version = EvaluationDatasetVersion(pk=7, dataset=EvaluationDataset(pk=3), status="published")
        config = case_config()
        config["assessment"] = {"objective": "检索后正确回答", "scope": ["当前住址", "无证据拒答"], "exclusions": ["记忆写入"], "score_interpretation": "正确为100分"}
        return EvaluationCase(pk=1, name="记忆问答", project_product=product, dataset_version=version, description="已有说明", config=config)

    def test_legacy_notes_are_visible_through_http_and_mcp_without_writing(self):
        case = self.case()
        original = deepcopy(case.config)
        description = case_description(case)
        for value in ("已有说明", "测评目标：检索后正确回答", "覆盖范围：当前住址；无证据拒答", "不覆盖：记忆写入", "评分口径：正确为100分"):
            self.assertIn(value, description)
        with patch("src.apps.evaluation.api.serializers.case.ProjectRelationSerializer.to_representation", return_value={"id": 1}):
            self.assertEqual(CaseSerializer().to_representation(case)["description"], description)
        self.assertEqual(case_record(case)["description"], description)
        self.assertEqual(case_summary(case)["description"], description)
        self.assertEqual(case.config, original)
        self.assertEqual(case.description, "已有说明")

    def test_configuration_save_moves_notes_into_existing_description_field(self):
        case = self.case()
        with patch.object(EvaluationCaseService, "selected_items", return_value=[]):
            result = EvaluationCaseService.normalize({"config": {key: value for key, value in case.config.items() if key != "assessment"}}, case)
        self.assertEqual(result["description"], case_description(case))
        self.assertNotIn("assessment", result["config"])
        self.assertIn("assessment", case.config)

    def test_external_edit_can_replace_or_clear_description_without_resurrecting_notes(self):
        case = self.case()
        for description in ("Given 数据已导入\nWhen 检索\nThen 命中预期记忆", ""):
            with patch.object(EvaluationCaseService, "selected_items", return_value=[]):
                result = EvaluationCaseService.normalize({"description": description}, case)
            self.assertEqual(result["description"], description)
            self.assertNotIn("config", result, "Editing case metadata must not validate or rewrite execution configuration")

    def test_status_only_update_does_not_write_description_or_configuration(self):
        case = self.case()
        with patch.object(EvaluationCaseService, "selected_items", return_value=[]):
            result = EvaluationCaseService.normalize({"status": "draft"}, case)
        self.assertNotIn("description", result)
        self.assertNotIn("config", result)

    def test_copy_does_not_append_duplicate_scenario_sections(self):
        case = self.case()
        text = case_description(case)
        self.assertEqual(scenario_description(text, case.config["assessment"]), text)
