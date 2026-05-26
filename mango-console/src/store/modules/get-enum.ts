import { defineStore } from 'pinia'
import { getSystemEnum, getSystemEnumShare } from '@/api/system/system'

type StateValueType = null | { key: number; title: string }[]

interface EnumState {
  client: StateValueType
  cline_type: StateValueType
  method: StateValueType
  api_public_type: StateValueType
  api_auth_type: StateValueType
  api_auth_refresh_mode: StateValueType
  api_auth_refresh_status: StateValueType
  api_client: StateValueType
  notice: StateValueType
  status: StateValueType
  drive_type: StateValueType
  browser_type: StateValueType
  element_exp: StateValueType
  case_level: StateValueType
  ui_public: StateValueType
  element_ope: StateValueType
  api_parameter_type: StateValueType
  api_case_scenario_layer: StateValueType
  api_case_scenario_type: StateValueType
  api_case_scenario_tag: StateValueType
  product_type: StateValueType
  auto_type: StateValueType
  task_status: StateValueType
  environment_type: StateValueType
  test_case_type: StateValueType
  file_status: StateValueType
  file_type: StateValueType
  monitoring_task_status: StateValueType
  monitoring_log_status: StateValueType
  test_suite_notice: StateValueType
  database_type: StateValueType
  data_factory_source_mode: StateValueType
  data_factory_operation_type: StateValueType
  data_factory_generator_type: StateValueType
  data_factory_cleanup_strategy: StateValueType
  data_factory_template_config_status: StateValueType
  data_factory_template_usage_scope: StateValueType
  data_factory_execution_source: StateValueType
  data_factory_execution_stage: StateValueType
  data_factory_execution_status: StateValueType
  data_factory_cleanup_status: StateValueType
  colors: string[]
  status_colors: string[]
}

let enumRequest: Promise<void> | null = null

export const useEnum = defineStore('get-enum', {
  state: (): EnumState => ({
    client: [],
    cline_type: [],
    method: [],
    api_public_type: [],
    api_auth_type: [],
    api_auth_refresh_mode: [],
    api_auth_refresh_status: [],
    api_client: [],
    notice: [],
    status: [],
    drive_type: [],
    browser_type: [],
    element_exp: [],
    case_level: [],
    ui_public: [],
    element_ope: [],
    api_parameter_type: [],
    api_case_scenario_layer: [],
    api_case_scenario_type: [],
    api_case_scenario_tag: [],
    product_type: [],
    auto_type: [],
    task_status: [],
    environment_type: [],
    test_case_type: [],
    file_status: [],
    file_type: [],
    monitoring_task_status: [],
    monitoring_log_status: [],
    test_suite_notice: [],
    database_type: [],
    data_factory_source_mode: [],
    data_factory_operation_type: [],
    data_factory_generator_type: [],
    data_factory_cleanup_strategy: [],
    data_factory_template_config_status: [],
    data_factory_template_usage_scope: [],
    data_factory_execution_source: [],
    data_factory_execution_stage: [],
    data_factory_execution_status: [],
    data_factory_cleanup_status: [],
    colors: [
      'cyan',
      'orangered',
      'orange',
      'gold',
      'lime',
      'green',
      'cyan',
      'blue',
      'red',
      'arcoblue',
      'purple',
      'pinkpurple',
      'gray',
      'magenta',
    ],
    status_colors: ['red', 'green', 'gold', 'gray'],
  }),
  getters: {},
  actions: {
    hasEnumData() {
      return Array.isArray(this.method) && this.method.length > 0
    },
    setEnumData(data: any) {
      this.client = data.client || data.cline_type || []
      this.cline_type = data.cline_type || []
      this.method = data.method || []
      this.api_public_type = data.api_public_type || []
      this.api_auth_type = data.api_auth_type || []
      this.api_auth_refresh_mode = data.api_auth_refresh_mode || []
      this.api_auth_refresh_status = data.api_auth_refresh_status || []
      this.api_client = data.api_client || []
      this.notice = data.notice || []
      this.status = data.status || []
      this.drive_type = data.drive_type || []
      this.browser_type = data.browser_type || []
      this.element_exp = data.element_exp || []
      this.case_level = data.case_level || []
      this.ui_public = data.ui_public || []
      this.element_ope = data.element_ope || []
      this.api_parameter_type = data.api_parameter_type || []
      this.api_case_scenario_layer = data.api_case_scenario_layer || []
      this.api_case_scenario_type = data.api_case_scenario_type || []
      this.api_case_scenario_tag = data.api_case_scenario_tag || []
      this.product_type = data.product_type || []
      this.auto_type = data.auto_type || []
      this.task_status = data.task_status || []
      this.environment_type = data.environment_type || []
      this.test_case_type = data.test_case_type || []
      this.file_status = data.file_status || []
      this.file_type = data.file_type || []
      this.monitoring_task_status = data.monitoring_task_status || []
      this.monitoring_log_status = data.monitoring_log_status || []
      this.test_suite_notice = data.test_suite_notice || []
      this.database_type = data.database_type || []
      this.data_factory_source_mode = data.data_factory_source_mode || []
      this.data_factory_operation_type = data.data_factory_operation_type || []
      this.data_factory_generator_type = data.data_factory_generator_type || []
      this.data_factory_cleanup_strategy = data.data_factory_cleanup_strategy || []
      this.data_factory_template_config_status = data.data_factory_template_config_status || []
      this.data_factory_template_usage_scope = data.data_factory_template_usage_scope || []
      this.data_factory_execution_source = data.data_factory_execution_source || []
      this.data_factory_execution_stage = data.data_factory_execution_stage || []
      this.data_factory_execution_status = data.data_factory_execution_status || []
      this.data_factory_cleanup_status = data.data_factory_cleanup_status || []
    },
    getEnum(force = false) {
      if (!force && this.hasEnumData()) {
        return Promise.resolve()
      }
      if (enumRequest) {
        return enumRequest
      }
      enumRequest = getSystemEnum()
        .then((res) => {
          this.setEnumData(res.data)
        })
        .catch(console.log)
        .finally(() => {
          enumRequest = null
        })
      return enumRequest
    },
    getEnumShare() {
      return getSystemEnumShare()
        .then((res) => {
          this.setEnumData(res.data)
        })
        .catch(console.log)
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
