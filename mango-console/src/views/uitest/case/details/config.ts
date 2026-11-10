import { fieldNames } from '@/setting'

export const UI_CASE_RESULT_SOCKET_EVENTS = [
  'u_page_steps',
  'u_page_step_node_progress',
  'u_test_case',
  'u_test_suite_details',
] as const

export function createUiCaseVariableFields(
  environmentOptions: Array<{ key: string | number; title: string }>,
  getEnvironment: (item: unknown) => unknown,
  setEnvironment: (value: unknown, item: unknown) => void
) {
  return [
    {
      field: 'test_envs', label: '适用环境', type: 'select' as const,
      placeholder: '请选择被测环境', options: environmentOptions, fieldNames,
      multiple: true, className: 'mango-env-select',
      containerClassName: 'mango-case-custom-env-field',
      getValue: getEnvironment, setValue: setEnvironment,
    },
    {
      field: 'key', label: 'Key', type: 'input' as const,
      placeholder: '请输入缓存key', className: 'mango-case-custom-key-input',
      containerClassName: 'mango-case-custom-key-field', showTitle: true,
    },
    {
      field: 'value', label: 'Value', type: 'input' as const,
      placeholder: '请输入value', className: 'mango-case-custom-value-input',
      containerClassName: 'mango-case-custom-value-field', showTitle: true,
    },
  ]
}
