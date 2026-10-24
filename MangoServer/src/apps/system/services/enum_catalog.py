import hashlib
import json
from typing import Any

from django.conf import settings
from mangotools.enums import NoticeEnum
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.ai.enums import (
    AiAgentTaskStatusEnum,
    AiAgentTaskTypeEnum,
    AiAgentToolCallStatusEnum,
    AiMcpAuthTypeEnum,
    AiMcpStatusEnum,
    AiMcpToolRiskLevelEnum,
    AiMcpTransportTypeEnum,
    AiMcpUseTypeEnum,
    AiSkillStatusEnum,
    AiSkillTypeEnum,
)
from src.apps.auto_api.enums import (
    ApiCaseConfigurationFilterEnum,
    ApiAuthRefreshModeEnum,
    ApiAuthRefreshStatusEnum,
    ApiAuthTypeEnum,
    ApiCaseScenarioLayerEnum,
    ApiCaseScenarioTagEnum,
    ApiCaseScenarioTypeEnum,
    ApiCaseReleaseStatusEnum,
    ApiClientEnum,
    ApiParameterTypeEnum,
    ApiPublicTypeEnum,
    MethodEnum,
)
from src.apps.evaluation.enums import (
    EvaluationStatusEnum, EvaluationVersionStatusEnum, EvaluationTargetTypeEnum,
    EvaluationCaseExecutionStatusEnum, EvaluationExecutionStatusEnum, EvaluationGradeStatusEnum, EvaluationVerdictEnum,
)
from src.apps.evaluation.enums.answer import EvaluationAnswerVerdictEnum
from src.apps.evaluation.enums.memory import MemoryFactStatusEnum
from src.apps.evaluation.enums.data_source import EvaluationItemSourceEnum
from src.apps.evaluation.enums.workflow import (EvaluationPreparationEnum, EvaluationSequenceEnum,
    EvaluationWorkflowStageEnum, EvaluationWorkflowScopeEnum, EvaluationWorkflowActionEnum, EvaluationTurnKindEnum)
from src.apps.auto_pytest.enums import FileStatusEnum, PytestAssetStatusEnum, PytestSourceStatusEnum, PytestCasePublicationStatusEnum
from src.apps.auto_ui.enums import (
    BrowserTypeEnum,
    DriveTypeEnum,
    ElementExpEnum,
    ElementOperationEnum,
    UiAuthRefreshModeEnum,
    UiAuthRefreshStatusEnum,
    UiAuthTypeEnum,
    UiCasePublicationStatusEnum,
    UiPublicTypeEnum,
)
from src.apps.data_factory.enums import (
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryEntityStatusChangeSourceEnum,
    DataFactoryExecutionSourceEnum,
    DataFactoryExecutionStageEnum,
    DataFactoryExecutionStatusEnum,
    DataFactoryGeneratorTypeEnum,
    DataFactoryOperationTypeEnum,
    DataFactorySourceModeEnum,
    DataFactoryTemplateConfigStatusEnum,
    DataFactoryTemplateUsageScopeEnum,
)
from src.apps.functional_test.enums import (
    FunctionalCaseStatusEnum,
    FunctionalTestContextContentTypeEnum,
    FunctionalTestContextKeyEnum,
    FunctionalTestContextParseStatusEnum,
    FunctionalTestContextUrlTypeEnum,
    FunctionalTestDefectPriorityEnum,
    FunctionalTestDefectResolutionEnum,
    FunctionalTestDefectSeverityEnum,
    FunctionalTestDefectSourceEnum,
    FunctionalTestDefectStatusEnum,
    FunctionalTestDefectTypeEnum,
    FunctionalTestIterationStatusEnum,
    FunctionalTestPlanScopeTypeEnum,
    FunctionalTestPlanStatusEnum,
    FunctionalTestRequirementStatusEnum,
    FunctionalTestResultEnum,
    ManualTestAutomationImpactStatusEnum,
    ManualTestAutomationTypeEnum,
    ManualTestChangeStatusEnum,
    ManualTestOptimizeStatusEnum,
    ManualTestRelationTypeEnum,
    ManualTestSourceTypeEnum,
    ManualTestSuiteStatusEnum,
    ManualTestSyncStatusEnum,
    ManualTestTypeEnum,
)
from src.apps.monitoring.enums import MonitoringLogStatusEnum, MonitoringTaskStatusEnum
from src.apps.system.enums import ClientTypeEnum, TestSuiteNoticeEnum
from src.apps.task_center.enums.execution import AutomationExecutionSceneEnum, AutomationExecutionScopeEnum, ReportRetentionPolicyEnum
from src.apps.test_center.enums import CaseLevelEnum, TestCaseTypeEnum, ReportFailureReasonEnum
from src.apps.test_center.enums.data_source import DataSourceCategoryEnum, DataSourceTypeEnum
from src.apps.test_center.enums.environment import AutoTypeEnum, EnvironmentEnum
from src.apps.test_center.enums.product import ProductTypeEnum


class EnumCatalogService:
    @classmethod
    def catalog(cls) -> dict[str, Any]:
        enum_data = {
            'cline_type': ClientTypeEnum.get_option(),
            'method': MethodEnum.get_option(),
            'api_public_type': ApiPublicTypeEnum.get_option(),
            'api_auth_type': ApiAuthTypeEnum.get_option(),
            'api_auth_refresh_mode': ApiAuthRefreshModeEnum.get_option(),
            'api_auth_refresh_status': ApiAuthRefreshStatusEnum.get_option(),
            'api_client': ApiClientEnum.get_option(),
            'notice': NoticeEnum.get_option(),
            'status': StatusEnum.get_option(),
            'drive_type': DriveTypeEnum.get_option(),
            'browser_type': BrowserTypeEnum.get_option(),
            'element_exp': ElementExpEnum.get_option(),
            'case_level': CaseLevelEnum.get_option(),
            'ui_public': UiPublicTypeEnum.get_option(),
            'ui_auth_type': UiAuthTypeEnum.get_option(),
            'ui_case_publication_status': UiCasePublicationStatusEnum.get_option(),
            'ui_auth_refresh_mode': UiAuthRefreshModeEnum.get_option(),
            'ui_auth_refresh_status': UiAuthRefreshStatusEnum.get_option(),
            'element_ope': ElementOperationEnum.get_option(),
            'api_parameter_type': ApiParameterTypeEnum.get_option(),
            'api_case_scenario_layer': ApiCaseScenarioLayerEnum.get_option(),
            'api_case_scenario_type': ApiCaseScenarioTypeEnum.get_option(),
            'api_case_configuration_filter': ApiCaseConfigurationFilterEnum.get_option(),
            'api_case_scenario_tag': ApiCaseScenarioTagEnum.get_option(),
            'api_case_release_status': ApiCaseReleaseStatusEnum.get_option(),
            'product_type': ProductTypeEnum.get_option(),
            'auto_type': AutoTypeEnum.get_option(),
            'data_source_category': DataSourceCategoryEnum.get_option(),
            'data_source_type': DataSourceTypeEnum.get_option(),
            'data_source_type_category': {
                key: DataSourceTypeEnum.category(key) for key in DataSourceTypeEnum.obj()
            },
            'database_type': DataSourceTypeEnum.get_option(),
            'data_factory_source_mode': DataFactorySourceModeEnum.get_option(),
            'data_factory_operation_type': DataFactoryOperationTypeEnum.get_option(),
            'data_factory_entity_status_change_source': DataFactoryEntityStatusChangeSourceEnum.get_option(),
            'data_factory_generator_type': DataFactoryGeneratorTypeEnum.get_option(),
            'data_factory_cleanup_strategy': DataFactoryCleanupStrategyEnum.get_option(),
            'data_factory_template_config_status': DataFactoryTemplateConfigStatusEnum.get_option(),
            'data_factory_template_usage_scope': DataFactoryTemplateUsageScopeEnum.get_option(),
            'data_factory_execution_source': DataFactoryExecutionSourceEnum.get_option(),
            'data_factory_execution_stage': DataFactoryExecutionStageEnum.get_option(),
            'data_factory_execution_status': DataFactoryExecutionStatusEnum.get_option(),
            'data_factory_cleanup_status': DataFactoryCleanupStatusEnum.get_option(),
            'evaluation_case_status': EvaluationStatusEnum.get_option(),
            'evaluation_version_status': EvaluationVersionStatusEnum.get_option(),
            'evaluation_target_type': EvaluationTargetTypeEnum.get_option(),
            'evaluation_execution_status': EvaluationCaseExecutionStatusEnum.get_option(),
            'evaluation_item_execution_status': EvaluationExecutionStatusEnum.get_option(),
            'evaluation_grade_status': EvaluationGradeStatusEnum.get_option(),
            'evaluation_verdict': EvaluationVerdictEnum.get_option(),
            'evaluation_answer_verdict': EvaluationAnswerVerdictEnum.get_option(),
            'evaluation_memory_fact_status': MemoryFactStatusEnum.get_option(),
            'evaluation_preparation': EvaluationPreparationEnum.get_option(),
            'evaluation_item_source': EvaluationItemSourceEnum.get_option(),
            'evaluation_sequence': EvaluationSequenceEnum.get_option(),
            'evaluation_workflow_stage': EvaluationWorkflowStageEnum.get_option(),
            'evaluation_workflow_scope': EvaluationWorkflowScopeEnum.get_option(),
            'evaluation_workflow_action': EvaluationWorkflowActionEnum.get_option(),
            'evaluation_turn_kind': EvaluationTurnKindEnum.get_option(),
            'task_status': TaskEnum.get_option(),
            'environment_type': EnvironmentEnum.get_option(),
            'environment_type_defaults': [
                {'key': key, 'title': title} for key, title in EnvironmentEnum.default_obj().items()
            ],
            'automation_execution_scene': AutomationExecutionSceneEnum.get_option(),
            'automation_execution_scope': AutomationExecutionScopeEnum.get_option(),
            'report_retention_policy': ReportRetentionPolicyEnum.get_option(),
            'test_case_type': TestCaseTypeEnum.get_option(),
            'report_failure_reason': ReportFailureReasonEnum.get_option(),
            'file_status': FileStatusEnum.get_option(),
            'pytest_source_status': PytestSourceStatusEnum.get_option(),
            'pytest_asset_status': PytestAssetStatusEnum.get_option(),
            'pytest_case_publication_status': PytestCasePublicationStatusEnum.get_option(),
            'monitoring_task_status': MonitoringTaskStatusEnum.get_option(),
            'monitoring_log_status': MonitoringLogStatusEnum.get_option(),
            'test_suite_notice': TestSuiteNoticeEnum.get_option(),
            'ai_skill_status': AiSkillStatusEnum.get_option(),
            'ai_skill_type': AiSkillTypeEnum.get_option(),
            'ai_mcp_status': AiMcpStatusEnum.get_option(),
            'ai_mcp_transport_type': AiMcpTransportTypeEnum.get_option(),
            'ai_mcp_auth_type': AiMcpAuthTypeEnum.get_option(),
            'ai_mcp_use_type': AiMcpUseTypeEnum.get_option(),
            'ai_mcp_tool_risk_level': AiMcpToolRiskLevelEnum.get_option(),
            'ai_agent_task_type': AiAgentTaskTypeEnum.get_option(),
            'ai_agent_task_status': AiAgentTaskStatusEnum.get_option(),
            'ai_agent_tool_call_status': AiAgentToolCallStatusEnum.get_option(),
            'manual_test_type': ManualTestTypeEnum.get_option(),
            'manual_test_source_type': ManualTestSourceTypeEnum.get_option(),
            'manual_test_sync_status': ManualTestSyncStatusEnum.get_option(),
            'manual_test_change_status': ManualTestChangeStatusEnum.get_option(),
            'manual_test_automation_impact_status': ManualTestAutomationImpactStatusEnum.get_option(),
            'manual_test_automation_type': ManualTestAutomationTypeEnum.get_option(),
            'manual_test_relation_type': ManualTestRelationTypeEnum.get_option(),
            'manual_test_optimize_status': ManualTestOptimizeStatusEnum.get_option(),
            'functional_case_status': FunctionalCaseStatusEnum.get_option(),
            'functional_test_plan_scope_type': FunctionalTestPlanScopeTypeEnum.get_option(),
            'functional_test_plan_status': FunctionalTestPlanStatusEnum.get_option(),
            'functional_test_result': FunctionalTestResultEnum.get_option(),
            'functional_test_iteration_status': FunctionalTestIterationStatusEnum.get_option(),
            'functional_test_requirement_status': FunctionalTestRequirementStatusEnum.get_option(),
            'manual_test_suite_status': ManualTestSuiteStatusEnum.get_option(),
            'functional_test_defect_source': FunctionalTestDefectSourceEnum.get_option(),
            'functional_test_defect_type': FunctionalTestDefectTypeEnum.get_option(),
            'functional_test_defect_severity': FunctionalTestDefectSeverityEnum.get_option(),
            'functional_test_defect_priority': FunctionalTestDefectPriorityEnum.get_option(),
            'functional_test_defect_status': FunctionalTestDefectStatusEnum.get_option(),
            'functional_test_defect_resolution': FunctionalTestDefectResolutionEnum.get_option(),
            'functional_test_context_key': FunctionalTestContextKeyEnum.get_option(),
            'functional_test_context_content_type': FunctionalTestContextContentTypeEnum.get_option(),
            'functional_test_context_url_type': FunctionalTestContextUrlTypeEnum.get_option(),
            'functional_test_context_parse_status': FunctionalTestContextParseStatusEnum.get_option(),
            'assertion_result_display_max_length': settings.ASSERTION_RESULT_DISPLAY_MAX_LENGTH,
        }
        return cls.build(enum_data)

    @staticmethod
    def build(enum_data: dict[str, Any]) -> dict[str, Any]:
        serialized = json.dumps(
            enum_data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(',', ':'),
        )
        version = hashlib.sha256(serialized.encode('utf-8')).hexdigest()[:16]
        return {
            'enum_version': version,
            **enum_data,
        }
