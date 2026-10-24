import { defineStore } from 'pinia'
import { getSystemEnum, getSystemEnumShare } from '@/api/system/system'

type EnumOption = { key: number | string; title: string }
type StateValueType = EnumOption[]

const ENUM_KEYS = [
  'cline_type',
  'method',
  'api_public_type',
  'api_auth_type',
  'api_auth_refresh_mode',
  'api_auth_refresh_status',
  'api_client',
  'notice',
  'status',
  'drive_type',
  'browser_type',
  'element_exp',
  'case_level',
  'ui_public',
  'ui_auth_type',
  'ui_case_publication_status',
  'pytest_case_publication_status',
  'ui_auth_refresh_mode',
  'ui_auth_refresh_status',
  'element_ope',
  'api_parameter_type',
  'api_case_scenario_layer',
  'api_case_scenario_type',
  'api_case_configuration_filter',
  'api_case_scenario_tag',
  'product_type',
  'auto_type',
  'data_source_category',
  'data_source_type',
  'database_type',
  'data_factory_source_mode',
  'data_factory_operation_type',
  'data_factory_entity_status_change_source',
  'data_factory_generator_type',
  'data_factory_cleanup_strategy',
  'data_factory_template_config_status',
  'data_factory_template_usage_scope',
  'data_factory_execution_source',
  'data_factory_execution_stage',
  'data_factory_execution_status',
  'data_factory_cleanup_status',
  'task_status',
  'evaluation_case_status',
  'evaluation_version_status',
  'evaluation_target_type',
  'evaluation_execution_status',
  'evaluation_item_execution_status',
  'evaluation_grade_status',
  'evaluation_verdict',
  'evaluation_answer_verdict',
  'evaluation_memory_fact_status',
  'evaluation_preparation',
  'evaluation_item_source',
  'evaluation_sequence',
  'evaluation_workflow_stage',
  'evaluation_workflow_scope',
  'evaluation_workflow_action',
  'evaluation_turn_kind',
  'environment_type',
  'environment_type_defaults',
  'automation_execution_scene',
  'automation_execution_scope',
  'report_retention_policy',
  'test_case_type',
  'report_failure_reason',
  'file_status',
  'pytest_source_status',
  'pytest_asset_status',
  'monitoring_task_status',
  'monitoring_log_status',
  'test_suite_notice',
  'ai_skill_status',
  'ai_skill_type',
  'ai_mcp_status',
  'ai_mcp_transport_type',
  'ai_mcp_auth_type',
  'ai_mcp_use_type',
  'ai_mcp_tool_risk_level',
  'ai_agent_task_type',
  'ai_agent_task_status',
  'ai_agent_tool_call_status',
  'manual_test_type',
  'manual_test_source_type',
  'manual_test_sync_status',
  'manual_test_change_status',
  'manual_test_automation_impact_status',
  'manual_test_automation_type',
  'manual_test_relation_type',
  'manual_test_optimize_status',
  'functional_case_status',
  'functional_test_plan_scope_type',
  'functional_test_plan_status',
  'functional_test_result',
  'functional_test_iteration_status',
  'functional_test_requirement_status',
  'manual_test_suite_status',
  'functional_test_defect_source',
  'functional_test_defect_type',
  'functional_test_defect_severity',
  'functional_test_defect_priority',
  'functional_test_defect_status',
  'functional_test_defect_resolution',
  'functional_test_context_key',
  'functional_test_context_content_type',
  'functional_test_context_url_type',
  'functional_test_context_parse_status',
] as const

type EnumKey = (typeof ENUM_KEYS)[number]
type EnumState = Record<EnumKey, StateValueType> & {
  enumVersion: string
  data_source_type_category: Record<number, number>
  assertion_result_display_max_length: number
  colors: string[]
  status_colors: string[]
}

function createEnumState(): EnumState {
  const enumValues = Object.fromEntries(ENUM_KEYS.map((key) => [key, []])) as Record<
    EnumKey,
    StateValueType
  >
  return {
    ...enumValues,
    enumVersion: '',
    data_source_type_category: {},
    assertion_result_display_max_length: 0,
    // 红色与绿色仅用于失败、成功等结果状态，业务分类使用独立配色池。
    colors: [
      'arcoblue',
      'orange',
      'purple',
      'cyan',
      'gold',
      'pinkpurple',
      'blue',
      'magenta',
      'gray',
      'purple',
      'cyan',
      'arcoblue',
      'gold',
      'pinkpurple',
      'orange',
      'blue',
      'magenta',
      'gray',
      'cyan',
      'purple',
    ],
    status_colors: ['red', 'green', 'gold', 'gray', 'orange', 'gray', 'gray'],
  }
}

let enumRequest: Promise<void> | null = null
let enumValidated = false

export const useEnum = defineStore('get-enum', {
  state: createEnumState,
  getters: {},
  actions: {
    hasEnumData() {
      return (
        Array.isArray(this.method) &&
        this.method.length > 0 &&
        Array.isArray(this.api_case_configuration_filter) &&
        this.api_case_configuration_filter.length > 0 &&
        Array.isArray(this.environment_type_defaults) &&
        this.environment_type_defaults.length > 0 &&
        Array.isArray(this.ai_agent_task_type) &&
        this.ai_agent_task_type.length > 0 &&
        Array.isArray(this.ui_auth_type) &&
        this.ui_auth_type.length > 0 &&
        Array.isArray(this.automation_execution_scene) &&
        this.automation_execution_scene.length > 0 &&
        Array.isArray(this.automation_execution_scope) &&
        this.automation_execution_scope.length > 0 &&
        Array.isArray(this.report_retention_policy) && this.report_retention_policy.length > 0 &&
        Array.isArray(this.data_factory_entity_status_change_source) &&
        this.data_factory_entity_status_change_source.length > 0 &&
        Array.isArray(this.functional_test_iteration_status) &&
        this.functional_test_iteration_status.length > 0 &&
        Array.isArray(this.manual_test_suite_status) &&
        this.manual_test_suite_status.length > 0 &&
        Array.isArray(this.functional_test_defect_status) &&
        this.functional_test_defect_status.length > 0
      )
    },
    setEnumData(data: Record<string, unknown>) {
      ENUM_KEYS.forEach((key) => {
        const value = data[key]
        this[key] = Array.isArray(value) ? (value as EnumOption[]) : []
      })
      const categoryMap = data.data_source_type_category
      this.data_source_type_category =
        categoryMap && typeof categoryMap === 'object'
          ? (categoryMap as Record<number, number>)
          : {}
      this.enumVersion = typeof data.enum_version === 'string' ? data.enum_version : ''
      const assertionResultDisplayMaxLength = Number(data.assertion_result_display_max_length)
      this.assertion_result_display_max_length =
        Number.isInteger(assertionResultDisplayMaxLength) && assertionResultDisplayMaxLength > 0
          ? assertionResultDisplayMaxLength
          : 0
    },
    getEnum(force = false) {
      if (!force && enumValidated && this.hasEnumData()) {
        return Promise.resolve()
      }
      if (enumRequest) {
        return enumRequest
      }
      enumRequest = getSystemEnum()
        .then((res) => {
          this.setEnumData(res.data)
          enumValidated = true
        })
        .catch((error) => {
          console.error('获取系统枚举失败', error)
          if (!this.hasEnumData()) throw error
        })
        .finally(() => {
          enumRequest = null
        })
      return enumRequest
    },
    getEnumShare() {
      return getSystemEnumShare()
        .then((res) => {
          this.setEnumData(res.data)
          enumValidated = true
        })
        .catch((error) => {
          console.error('获取共享枚举失败', error)
        })
    },
  },
  presist: {
    enable: true,
    resetToState: true,
    option: {
      key: 'get-enum-v2',
    },
  },
})
