import { defineStore } from 'pinia'
import { getSystemEnum } from '@/api/system/system'

type StateValueType = null | { key: number; title: string }[]

interface EnumState {
  cline_type: StateValueType
  method: StateValueType
  api_public_type: StateValueType
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
  colors: string[]
  status_colors: string[]
}

export const useEnum = defineStore('get-enum', {
  state: (): EnumState => ({
    cline_type: [],
    method: [],
    api_public_type: [],
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
    colors: [
      'magenta',
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
    ],
    status_colors: ['red', 'green', 'gold', 'gray'],
  }),
  getters: {},
  actions: {
    getEnum() {
      getSystemEnum()
        .then((res) => {
          if (!this.client) {
            this.cline_type = res.data.cline_type
            this.method = res.data.method
            this.api_public_type = res.data.api_public_type
            this.api_client = res.data.api_client
            this.notice = res.data.notice
            this.status = res.data.status
            this.drive_type = res.data.drive_type
            this.browser_type = res.data.browser_type
            this.element_exp = res.data.element_exp
            this.case_level = res.data.case_level
            this.ui_public = res.data.ui_public
            this.element_ope = res.data.element_ope
            this.api_parameter_type = res.data.api_parameter_type
            this.product_type = res.data.product_type
            this.auto_type = res.data.auto_type
            this.task_status = res.data.task_status
            this.environment_type = res.data.environment_type
            this.test_case_type = res.data.test_case_type
            this.file_status = res.data.file_status
            this.file_type = res.data.file_type
            this.monitoring_task_status = res.data.monitoring_task_status
            this.monitoring_log_status = res.data.monitoring_log_status
            this.test_suite_notice = res.data.test_suite_notice
          }
        })
        .catch(console.log)
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
