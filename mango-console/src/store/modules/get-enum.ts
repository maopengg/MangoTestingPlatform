import { defineStore } from 'pinia'
import { getSystemEnum } from '@/api/system/system'
type StateValueType = null | { key: number; title: string }[] | string[]
export const useEnum = defineStore('get-enum', {
  state: (): {
    cline_type: StateValueType
    method: StateValueType
    api_public_type: StateValueType
    api_client: StateValueType
    notice: StateValueType
    status: StateValueType
    drive_type: StateValueType
    browser_type: StateValueType
    element_exp: StateValueType
    auto_test_type: StateValueType
    case_level: StateValueType
    ui_public: StateValueType
    element_ope: StateValueType
    api_parameter_type: StateValueType
    device: StateValueType
    product_type: StateValueType
    auto_type: StateValueType
    task_status: StateValueType
    environment_type: StateValueType
    colors: string[]
    status_colors: string[]
  } => {
    return {
      cline_type: null,
      method: null,
      api_public_type: null,
      api_client: null,
      notice: null,
      status: null,
      drive_type: null,
      browser_type: null,
      element_exp: null,
      auto_test_type: null,
      case_level: null,
      ui_public: null,
      element_ope: null,
      api_parameter_type: null,
      device: null,
      product_type: null,
      auto_type: null,
      task_status: null,
      environment_type: null,
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
      status_colors: ['red', 'green', 'gold', 'lime'],
    }
  },
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
            this.auto_test_type = res.data.auto_test_type
            this.case_level = res.data.case_level
            this.ui_public = res.data.ui_public
            this.element_ope = res.data.element_ope
            this.api_parameter_type = res.data.api_parameter_type
            this.device = res.data.device
            this.product_type = res.data.product_type
            this.auto_type = res.data.auto_type
            this.task_status = res.data.task_status
            this.environment_type = res.data.environment_type
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
