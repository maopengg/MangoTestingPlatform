import type {
  FunctionalGridColumn,
  FunctionalGridOption,
} from '@/components/table/functional-case-grid'
import type { useEnum } from '@/store/modules/get-enum'

export const CASE_LIBRARY_GRID_KEY = 'functional-case-library'
export const CASE_LIBRARY_GRID_LAYOUT_VERSION = 2
export const CASE_SPREADSHEET_FIELDS = [
  ['case_no', '用例编号'],
  ['title', '用例标题'],
  ['project_product_id', '项目产品ID'],
  ['module_id', '模块ID'],
  ['category_level_1', '分类一'],
  ['category_level_2', '分类二'],
  ['category_level_3', '分类三'],
  ['priority', '优先级'],
  ['test_types', '测试类型'],
  ['story_refs', '关联用户故事'],
  ['precondition', '前置条件'],
  ['test_point', '测试场景'],
  ['test_steps', '测试步骤JSON'],
  ['expected_result', '预期结果'],
  ['acceptance_source', '验收标准来源'],
  ['test_data', '测试数据'],
  ['owner_id', '负责人ID'],
  ['automation_status', '自动化状态'],
  ['bindings', '自动化绑定'],
  ['scenario_layer', '测试层级'],
  ['scenario_type', '验证类型'],
  ['scenario_tags', '执行场景'],
  ['status', '资产状态'],
  ['remark', '备注'],
] as const
export const AUTOMATION_STATUS_OPTIONS = [
  { label: '未自动化', value: 'not_automated', colorToken: '--m-muted' },
  { label: '已自动化', value: 'automated', colorToken: '--m-success' },
]

const ENUM_COLOR_TOKENS = {
  priority: { 0: '--m-danger', 1: '--m-warning', 2: '--m-primary', 3: '--m-muted' },
  testType: {
    0: '--m-muted',
    1: '--m-primary',
    2: '--m-success',
    3: '--m-warning',
    4: '--m-danger',
    5: '--m-chart-5',
  },
  scenarioLayer: { 0: '--m-primary', 1: '--m-warning', 2: '--m-danger' },
  scenarioType: {
    0: '--m-success',
    1: '--m-danger',
    2: '--m-warning',
    3: '--m-primary',
    4: '--m-chart-5',
    5: '--m-chart-2',
  },
  scenarioTag: {
    routine_regression: '--m-primary',
    release_verification: '--m-success',
    smoke_verification: '--m-warning',
    inspection: '--m-chart-5',
    stability_monitoring: '--m-chart-2',
    data_verification: '--m-chart-3',
    effectiveness_test: '--m-chart-4',
    production_inspection: '--m-danger',
    production_regression: '--m-muted',
    temporary_validation: '--m-primary',
    performance_test: '--m-chart-5',
  },
  assetStatus: { 0: '--m-warning', 1: '--m-success', 2: '--m-danger' },
} as const

const enumOptions = (
  items: Array<{ key: string | number; title: string }> = [],
  colors: Record<string, string>
): FunctionalGridOption[] =>
  items.map((item) => ({
    label: item.title,
    value: item.key,
    colorToken: colors[String(item.key)] || '--m-primary',
  }))

export const formatAutomationBindings = (bindings: unknown = []) => {
  if (!Array.isArray(bindings) || bindings.length === 0) return '-'
  return (
    bindings
      .filter(
        (binding): binding is Record<string, unknown> =>
          !!binding && typeof binding === 'object' && !Array.isArray(binding)
      )
      .filter((binding) => binding.automation_type === 0 || binding.automation_type === 1)
      .map((binding) => {
        const type = binding.automation_type === 0 ? 'API' : 'UI'
        const caseId = binding.automation_case_id || binding.api_case_id || binding.ui_case_id
        const name = String(binding.automation_case_name || '').trim()
        return `${type} Case ID: ${caseId || '-'}${name ? ` · ${name}` : ''}`
      })
      .join('；') || '-'
  )
}

interface GridUserOption {
  key?: string | number
  id?: string | number
  title?: string
  name?: string
  username?: string
}
const userOptions = (users: GridUserOption[] = []): FunctionalGridOption[] =>
  users.flatMap((item) => {
    const value = item.key ?? item.id
    if (value === undefined) return []
    return [
      {
        label: item.title || item.name || item.username || `用户 ${item.key ?? item.id}`,
        value,
      },
    ]
  })

type GridEnums = Pick<
  ReturnType<typeof useEnum>,
  | 'case_level'
  | 'manual_test_type'
  | 'api_case_scenario_layer'
  | 'api_case_scenario_type'
  | 'api_case_scenario_tag'
  | 'functional_case_status'
>
export const createCaseLibraryColumns = (
  enums: GridEnums,
  users: GridUserOption[] = []
): FunctionalGridColumn[] => [
  { field: 'case_no', title: '用例编号', width: 130, fixed: 'left', sortable: true },
  { field: 'title', title: '用例标题', width: 240, fixed: 'left', sortable: true },
  { field: 'category_level_1', title: '分类一', width: 130 },
  { field: 'category_level_2', title: '分类二', width: 130 },
  { field: 'category_level_3', title: '分类三', width: 130 },
  {
    field: 'priority',
    title: '优先级',
    width: 90,
    align: 'center',
    options: enumOptions(enums.case_level, ENUM_COLOR_TOKENS.priority),
  },
  {
    field: 'test_types',
    title: '测试类型',
    width: 150,
    align: 'center',
    multiple: true,
    options: enumOptions(enums.manual_test_type, ENUM_COLOR_TOKENS.testType),
  },
  { field: 'story_refs', title: '用户故事', width: 150, editable: false },
  { field: 'precondition', title: '前置条件', width: 200, editor: 'textarea' },
  { field: 'test_point', title: '测试场景', width: 240, editor: 'textarea' },
  { field: 'test_steps', title: '测试步骤', width: 120, editable: false },
  { field: 'expected_result', title: '预期结果', width: 220, editor: 'textarea' },
  { field: 'acceptance_source', title: '验收来源', width: 200, editor: 'textarea' },
  { field: 'test_data', title: '测试数据', width: 180, editor: 'textarea' },
  {
    field: 'scenario_layer',
    title: '测试层级',
    width: 110,
    align: 'center',
    options: enumOptions(enums.api_case_scenario_layer, ENUM_COLOR_TOKENS.scenarioLayer),
  },
  {
    field: 'scenario_type',
    title: '验证类型',
    width: 110,
    align: 'center',
    options: enumOptions(enums.api_case_scenario_type, ENUM_COLOR_TOKENS.scenarioType),
  },
  {
    field: 'scenario_tags',
    title: '执行场景',
    width: 180,
    align: 'center',
    multiple: true,
    valueAliases: {
      default: 'routine_regression',
      regression: 'routine_regression',
      smoke: 'smoke_verification',
    },
    options: enumOptions(enums.api_case_scenario_tag, ENUM_COLOR_TOKENS.scenarioTag),
  },
  {
    field: 'automation_status',
    title: '自动化状态',
    width: 120,
    align: 'center',
    valueAliases: { candidate: 'not_automated' },
    options: AUTOMATION_STATUS_OPTIONS,
  },
  { field: 'automation_bindings', title: '自动化绑定', width: 300, editable: false },
  { field: 'remark', title: '备注', width: 180, editor: 'textarea' },
  {
    field: 'status',
    title: '资产状态',
    width: 100,
    align: 'center',
    options: enumOptions(enums.functional_case_status, ENUM_COLOR_TOKENS.assetStatus),
  },
  {
    field: 'owner_id',
    title: '负责人',
    width: 120,
    align: 'center',
    options: userOptions(users),
  },
  { field: 'version_no', title: '版本', width: 72, editable: false },
  { field: 'update_time', title: '更新时间', width: 165, editable: false },
  {
    field: 'project_product_id',
    title: '项目/产品',
    width: 200,
    editor: 'project-product',
    displayField: 'project_product_path',
  },
  {
    field: 'module_id',
    title: '模块',
    width: 220,
    editor: 'module-cascader',
    displayField: 'module_path',
  },
]

export interface LibraryGridPreferences {
  layout_version?: number
  columns?: unknown
}

export function mergeLibraryGridColumns(
  defaults: FunctionalGridColumn[],
  preferences: LibraryGridPreferences
) {
  const aliases: Record<string, string> = {
    owner_name: 'owner_id',
    project_product_path: 'project_product_id',
    module_path: 'module_id',
  }
  const saved: Array<Pick<FunctionalGridColumn, 'field' | 'width' | 'visible'>> = []
  const seen = new Set<string>()
  for (const item of Array.isArray(preferences.columns) ? preferences.columns : []) {
    if (!item || typeof item !== 'object' || typeof item.field !== 'string') continue
    const field = aliases[item.field] ?? item.field
    if (seen.has(field) || !defaults.some((column) => column.field === field)) continue
    seen.add(field)
    saved.push({
      field,
      width:
        typeof item.width === 'number' && Number.isFinite(item.width) && item.width > 0
          ? item.width
          : undefined,
      visible: typeof item.visible === 'boolean' ? item.visible : undefined,
    })
  }
  const upgrade = Number(preferences.layout_version ?? 0) < CASE_LIBRARY_GRID_LAYOUT_VERSION
  const order = upgrade
    ? [
        ...saved.filter((item) => !['project_product_id', 'module_id'].includes(item.field)),
        ...['project_product_id', 'module_id'].flatMap((field) =>
          saved.filter((item) => item.field === field)
        ),
      ]
    : saved
  const columns = order.map((item) => {
    const column = defaults.find((value) => value.field === item.field)!
    return { ...column, width: item.width ?? column.width, visible: item.visible ?? column.visible }
  })
  return { columns: [...columns, ...defaults.filter((item) => !seen.has(item.field))], upgrade }
}
