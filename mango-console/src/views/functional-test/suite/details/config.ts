import type { TableColumnData } from '@arco-design/web-vue'

export const resourceContent = { text: 0, url: 1, file: 2, image: 3 } as const
export const resourceUrl = { normal: 0, feishu: 1 } as const
export const resourceCodeStyle = { width: '100%', height: '100%' }

export const AUTOMATION_TYPE_API = 0

export const AUTOMATION_TYPE_UI = 1

export const RESOURCE_KEY_REQUIREMENT_DOC = 0

export const RESOURCE_KEY_DEVELOPMENT_DESIGN = 1

export const RESOURCE_KEY_API_DOC = 2

export const RESOURCE_KEY_DEVELOPMENT_CODE = 3

export const RESOURCE_KEY_SQL_QUERY = 4

export const RESOURCE_KEY_RAW_CASE_DOC = 5

export const RESOURCE_KEY_PLATFORM_CASE = 6

export const RESOURCE_KEY_PAGE_DATA = 7

export const RESOURCE_KEY_TEST_UNDERSTANDING = 8

export const RESOURCE_CONTENT_URL = 1

export const requirementDocNavItem = {
  key: RESOURCE_KEY_REQUIREMENT_DOC,
  title: '需求文档',
  description: '用于核对测试用例是否有遗漏',
  tip: '需求文档记录业务场景、异常场景与验收点，便于核对用例覆盖。',
}

export const developmentDesignNavItem = {
  key: RESOURCE_KEY_DEVELOPMENT_DESIGN,
  title: '开发设计',
  description: '用于创建 API 接口、API 用例和数据工厂',
  tip: '开发设计记录接口实现方案、模块边界、核心流程和数据处理逻辑。',
}

export const apiDocNavItem = {
  key: RESOURCE_KEY_API_DOC,
  title: '接口文档',
  description: '用于创建 API 接口、API 用例和数据工厂',
  tip: '接口文档记录请求方法、路径、参数、响应、鉴权和错误码。',
}

export const developmentCodeNavItem = {
  key: RESOURCE_KEY_DEVELOPMENT_CODE,
  title: '开发代码',
  description: '用于识别数据库表关系并创建数据工厂',
  tip: '开发代码用于查阅落库逻辑、实体关系、枚举取值、字段默认值和依赖调用。',
}

export const sqlQueryNavItem = {
  key: RESOURCE_KEY_SQL_QUERY,
  title: 'SQL语句',
  description: '用于识别数据库表关系并创建数据工厂',
  tip: 'SQL语句用于记录表名、字段、关联条件和数据校验方式。',
}

export const rawCaseDocNavItem = {
  key: 'sync',
  title: '原始用例文档',
  description: '记录需求对应的原始用例文档',
  tip: '原始用例文档用于查阅来源内容并核对平台用例。',
}

export const rawCaseDocContextItem = {
  ...rawCaseDocNavItem,
  key: RESOURCE_KEY_RAW_CASE_DOC,
}

export const pageDataContextItem = {
  key: RESOURCE_KEY_PAGE_DATA,
  title: '页面数据',
  description: '用于补充页面实际数据和预期结果',
  tip: '页面数据记录页面字段、状态、展示数据和操作结果。',
}

export const testUnderstandingContextItem = {
  key: RESOURCE_KEY_TEST_UNDERSTANDING,
  title: '测试理解',
  description: '用于补充测试人员理解和风险点',
  tip: '测试理解记录需求边界、风险点、异常路径与验收关注点。',
}

export const platformCaseNavItem = {
  key: 'cases',
  title: '来源用例',
  description: '当前需求版本沉淀到用例库的功能用例',
  tip: '来源用例是当前需求版本沉淀到用例库的可复用资产，可继续维护字段和自动化绑定。',
}

export const contextNavItems = [
  requirementDocNavItem,
  developmentDesignNavItem,
  apiDocNavItem,
  developmentCodeNavItem,
  sqlQueryNavItem,
  rawCaseDocContextItem,
  pageDataContextItem,
  testUnderstandingContextItem,
]

export const navGroups = [
  { title: '产品角色', items: [requirementDocNavItem] },
  {
    title: '开发角色',
    items: [developmentDesignNavItem, apiDocNavItem, developmentCodeNavItem, sqlQueryNavItem],
  },
  {
    title: '测试角色',
    items: [rawCaseDocNavItem, pageDataContextItem, testUnderstandingContextItem],
  },
  { title: '交付产物', items: [platformCaseNavItem] },
]

export const allNavItems = navGroups.flatMap((group) => group.items)

export const contextFieldKeys = new Set<number | string>(contextNavItems.map((item) => item.key))

export const caseColumns: Array<TableColumnData & { key: string }> = [
  {
    title: '用例编号',
    key: 'case_no',
    dataIndex: 'case_no',
    width: 120,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 160,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块名称',
    key: 'module',
    dataIndex: 'module',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  { title: '标题', key: 'title', dataIndex: 'title', width: 240, ellipsis: true, tooltip: true },
  {
    title: '前置条件',
    key: 'precondition',
    dataIndex: 'precondition',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试场景',
    key: 'test_point',
    dataIndex: 'test_point',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试数据',
    key: 'test_data',
    dataIndex: 'test_data',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  { title: '测试类型', key: 'test_types', dataIndex: 'test_types', width: 220 },
  { title: '测试层级', key: 'scenario_layer', dataIndex: 'scenario_layer', width: 120 },
  { title: '验证类型', key: 'scenario_type', dataIndex: 'scenario_type', width: 110 },
  { title: '执行场景', key: 'scenario_tags', dataIndex: 'scenario_tags', width: 220 },
  {
    title: '自动化用例ID',
    key: 'automation_case_ids',
    dataIndex: 'automation_case_ids',
    width: 180,
  },
  { title: '变更', key: 'change_status', dataIndex: 'change_status', width: 100 },
  {
    title: '自动化影响',
    key: 'automation_impact_status',
    dataIndex: 'automation_impact_status',
    width: 120,
  },
  { title: '备注', key: 'remark', dataIndex: 'remark', width: 180, ellipsis: true, tooltip: true },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    fixed: 'right',
    width: 140,
  },
]

for (const column of caseColumns) {
  column.align = [
    'priority',
    'test_types',
    'scenario_layer',
    'scenario_type',
    'scenario_tags',
    'change_status',
    'automation_impact_status',
    'actions',
  ].includes(column.key)
    ? 'center'
    : 'left'
}

export const caseScrollWidth = caseColumns.reduce(
  (total, column) => total + Number(column.width || 0),
  0
)
