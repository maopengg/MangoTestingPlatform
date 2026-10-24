import type { TableColumnData } from '@arco-design/web-vue'

export const statusOptions = [
  { label: '待创建', value: 'pending_create' },
  { label: '已完成', value: 'completed' },
  { label: '暂不处理', value: 'deferred' },
  { label: '已移除', value: 'removed' },
]

export const changeStatusOptions = [
  { label: '新增', value: 'created' },
  { label: '修改', value: 'updated' },
  { label: '未变化', value: 'unchanged' },
  { label: '已删除', value: 'removed' },
]

export const validityOptions = [
  { label: '有效', value: 'valid' },
  { label: '待复核', value: 'pending_review' },
  { label: '失效', value: 'invalid' },
]

export const interfaceStatusOptions = [
  { label: '有效', value: 'active' },
  { label: '已移除', value: 'removed' },
]

export const apiInfoBindingOptions = [
  { label: '已绑定', value: 'bound' },
  { label: '未绑定', value: 'unbound' },
  { label: '候选冲突', value: 'ambiguous' },
  { label: '待确认', value: 'mismatch' },
]

export const interfaceColumns: TableColumnData[] = [
  { title: 'ID', dataIndex: 'id', slotName: 'id', width: 72, align: 'center' },
  {
    title: '接口名称',
    dataIndex: 'interface_name',
    slotName: 'interface_name',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  { title: 'Method', dataIndex: 'method', slotName: 'method', width: 90, align: 'center' },
  { title: 'URL', dataIndex: 'url', width: 300, ellipsis: true, tooltip: true },
  {
    title: '链路状态',
    dataIndex: 'resolution_status',
    slotName: 'resolution_status',
    width: 120,
    align: 'center',
  },
  {
    title: '生命周期',
    dataIndex: 'lifecycle_status',
    slotName: 'lifecycle_status',
    width: 110,
    align: 'center',
  },
  {
    title: 'ApiInfo绑定',
    dataIndex: 'api_info_binding_status',
    slotName: 'api_info_binding',
    width: 160,
    align: 'center',
  },
  {
    title: '接口归属模块',
    dataIndex: 'owner_module',
    slotName: 'owner_module',
    width: 210,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '自动化进度',
    dataIndex: 'coverage_rate',
    slotName: 'coverage_rate',
    width: 180,
    align: 'center',
  },
  { title: 'Case总数', dataIndex: 'case_count', width: 100, align: 'center' },
  {
    title: '有效自动化',
    dataIndex: 'effective_completed_case_count',
    width: 110,
    align: 'center',
  },
  {
    title: 'ApiCase已绑定',
    dataIndex: 'completed_case_count',
    width: 130,
    align: 'center',
  },
  {
    title: '暂不处理',
    dataIndex: 'deferred_case_count',
    width: 110,
    align: 'center',
  },
  {
    title: '覆盖有效性',
    dataIndex: 'valid_case_count',
    slotName: 'coverage_validity_stats',
    width: 190,
    align: 'center',
  },
  {
    title: '覆盖状态',
    dataIndex: 'coverage_status',
    slotName: 'coverage_status',
    width: 110,
    align: 'center',
  },
  { title: '仓库', dataIndex: 'repository_key', width: 170, ellipsis: true, tooltip: true },
  { title: '分支', dataIndex: 'branch', width: 150, ellipsis: true, tooltip: true },
  { title: '首次扫描', dataIndex: 'first_scan_id', slotName: 'first_scan', width: 100 },
  { title: '最近扫描', dataIndex: 'latest_scan_id', slotName: 'latest_scan', width: 100 },
  { title: '当前Commit', dataIndex: 'latest_commit_sha', slotName: 'latest_commit', width: 130 },
  { title: '变更', dataIndex: 'sync_action', slotName: 'sync_action', width: 100, align: 'center' },
  { title: '更新时间', dataIndex: 'update_time', width: 180 },
  { title: '项目/产品', dataIndex: 'project_product', slotName: 'project_product', width: 150 },
  {
    title: '模块',
    dataIndex: 'module',
    slotName: 'module',
    width: 190,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    slotName: 'actions',
    width: 160,
    fixed: 'right',
    align: 'center',
  },
]

export const tableScrollXByTab: Record<string, number> = {
  interfaces: 3190,
  cases: 3890,
  scans: 2050,
}

export const caseColumns: TableColumnData[] = [
  { title: 'ID', dataIndex: 'id', slotName: 'id', width: 72, align: 'center' },
  {
    title: 'Case标题',
    dataIndex: 'name',
    slotName: 'name',
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '接口名称 + Method + URL',
    dataIndex: 'interface_name',
    slotName: 'case_interface',
    width: 320,
  },
  {
    title: '测试场景',
    dataIndex: 'payload.test_scenario',
    slotName: 'test_scenario',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '核心断言',
    dataIndex: 'payload.core_assertion',
    slotName: 'core_assertion',
    width: 280,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试归属',
    dataIndex: 'test_ownership',
    slotName: 'test_ownership',
    width: 150,
    align: 'center',
  },
  {
    title: '测试层级',
    dataIndex: 'scenario_layer',
    slotName: 'scenario_layer',
    width: 130,
    align: 'center',
  },
  {
    title: '验证类型',
    dataIndex: 'scenario_type',
    slotName: 'scenario_type',
    width: 120,
    align: 'center',
  },
  {
    title: '执行场景',
    dataIndex: 'scenario_tags',
    slotName: 'scenario_tags',
    width: 180,
    align: 'left',
  },
  {
    title: '变更状态',
    dataIndex: 'change_status',
    slotName: 'change_status',
    width: 110,
    align: 'center',
  },
  {
    title: '覆盖有效性',
    dataIndex: 'coverage_validity',
    slotName: 'coverage_validity',
    width: 120,
    align: 'center',
  },
  { title: '当前状态', dataIndex: 'status', slotName: 'status', width: 110, align: 'center' },
  {
    title: '暂不处理原因',
    dataIndex: 'payload.remark',
    slotName: 'deferred_reason',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  { title: '自动化Case', dataIndex: 'api_case', slotName: 'api_case', width: 180 },
  {
    title: '执行结果',
    dataIndex: 'execution_result',
    slotName: 'execution_result',
    width: 120,
    align: 'center',
  },
  { title: '来源Key', dataIndex: 'source_key', width: 220, ellipsis: true, tooltip: true },
  {
    title: '最近Commit',
    dataIndex: 'current_commit',
    slotName: 'commit',
    width: 130,
    ellipsis: true,
    tooltip: true,
  },
  { title: '仓库', dataIndex: 'repository_key', width: 170, ellipsis: true, tooltip: true },
  { title: '分支', dataIndex: 'branch', width: 150, ellipsis: true, tooltip: true },
  { title: '更新时间', dataIndex: 'update_time', width: 170 },
  { title: '项目/产品', dataIndex: 'project_product', slotName: 'project_product', width: 150 },
  {
    title: '模块',
    dataIndex: 'module',
    slotName: 'module',
    width: 190,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    slotName: 'actions',
    width: 160,
    fixed: 'right',
    align: 'center',
  },
]

export const scanColumns: TableColumnData[] = [
  { title: 'ID', dataIndex: 'id', slotName: 'id', width: 72, align: 'center' },
  { title: '范围', dataIndex: 'scope_type', slotName: 'scope_type', width: 110, align: 'center' },
  { title: '模式', dataIndex: 'scan_mode', slotName: 'scan_mode', width: 110, align: 'center' },
  {
    title: '目标接口',
    dataIndex: 'target_interface',
    slotName: 'target_interface',
    width: 110,
    align: 'center',
  },
  { title: '仓库', dataIndex: 'repository_name', width: 180, ellipsis: true, tooltip: true },
  { title: '分支', dataIndex: 'branch', width: 150, ellipsis: true, tooltip: true },
  {
    title: 'Commit',
    dataIndex: 'commit_sha',
    slotName: 'commit',
    width: 160,
    ellipsis: true,
    tooltip: true,
  },
  { title: '状态', dataIndex: 'status', slotName: 'scan_status', width: 110, align: 'center' },
  {
    title: 'Case',
    dataIndex: 'summary.case_count',
    slotName: 'case_count',
    width: 100,
    align: 'center',
  },
  { title: '新增', dataIndex: 'summary.created', slotName: 'created', width: 90, align: 'center' },
  { title: '修改', dataIndex: 'summary.updated', slotName: 'updated', width: 90, align: 'center' },
  { title: '移除', dataIndex: 'summary.removed', slotName: 'removed', width: 90, align: 'center' },
  {
    title: '接口变更',
    dataIndex: 'summary.interface_count',
    slotName: 'interface_changes',
    width: 190,
    align: 'center',
  },
  { title: '完成时间', dataIndex: 'finished_at', width: 170 },
  { title: '项目/产品', dataIndex: 'project_product', slotName: 'project_product', width: 150 },
  {
    title: '模块',
    dataIndex: 'module',
    slotName: 'module',
    width: 190,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    slotName: 'actions',
    width: 160,
    fixed: 'right',
    align: 'center',
  },
]

export const labels: Record<string, string> = {
  pending_create: '待创建',
  completed: '已完成',
  completed_with_gaps: '审计完成（存在Gap）',
  deferred: '暂不处理',
  removed: '已移除',
  not_applicable: '不适用',
  passed: '执行通过',
  failed: '执行失败',
  partial: '部分通过',
  not_executed: '未执行',
  full: '完整扫描',
  incremental: '增量扫描',
  uploading: '上传中',
  cancelled: '已取消',
  created: '新增',
  updated: '修改',
  unchanged: '未变化',
  covered: '已覆盖',
  uncovered: '未覆盖',
  resolved: '链路完整',
  placeholder: '尚未完成解析',
  project: '项目接口盘点',
  gap: '未解析 Gap',
  module: '模块扫描',
  interface: '单接口扫描',
  valid: '有效',
  pending_review: '待复核',
  invalid: '失效',
  active: '有效',
  bound: '已绑定',
  unbound: '未绑定',
  ambiguous: '候选冲突',
  mismatch: '待确认',
}

export function tagColor(value: string) {
  if (['completed', 'passed', 'covered', 'resolved', 'valid', 'bound'].includes(value))
    return 'green'
  if (['failed', 'removed', 'placeholder', 'invalid', 'ambiguous'].includes(value)) return 'red'
  if (
    ['deferred', 'partial', 'gap', 'pending_review', 'mismatch', 'completed_with_gaps'].includes(
      value
    )
  )
    return 'orange'
  return 'blue'
}

export function changeStatusTagColor(value: string, colors: string[]) {
  const index = changeStatusOptions.findIndex((item) => item.value === value)
  return colors[index >= 0 ? index : 0]
}

const methodColorIndexes: Record<string, number> = {
  GET: 0,
  POST: 1,
  PUT: 2,
  DELETE: 3,
  OPTIONS: 4,
  DEAD: 5,
  PATCH: 6,
  MCP_CALL: 7,
  GRPC_CALL: 8,
  WEBSOCKET_CONNECT: 9,
}

export function methodTagColor(method: string, colors: string[]) {
  return colors[methodColorIndexes[String(method || '').toUpperCase()]] || 'gray'
}

const executionResultColorIndexes: Record<string, number> = {
  failed: 0,
  passed: 1,
  not_executed: 3,
  partial: 4,
  not_applicable: 5,
}

export function executionResultTagColor(result: string, statusColors: string[]) {
  return statusColors[executionResultColorIndexes[result]] || 'gray'
}

export function ownershipTagColor(value: string) {
  if (value === 'HTTP API自动化') return 'blue'
  if (value === '单元测试') return 'orange'
  if (value === '集成测试') return 'purple'
  return 'gray'
}
export const overviewFilters = [
  { value: 'all', label: '全部模块' },
  { value: 'scan', label: '未完整扫描' },
  { value: 'entry', label: '接口未录入' },
  { value: 'case', label: '自动化未完成' },
]

export const overviewModuleColumns: TableColumnData[] = [
  { title: 'ID', dataIndex: 'id', width: 72, align: 'center' },
  { title: '名称', dataIndex: 'name', width: 160, ellipsis: true, tooltip: true },
  { title: '扫描状态', slotName: 'scan', width: 240, ellipsis: true, tooltip: true },
  { title: '接口录入', slotName: 'entry', width: 180 },
  { title: '自动化场景', slotName: 'automation', width: 180 },
  { title: '暂不处理场景', dataIndex: 'deferred_count', width: 120, align: 'center' },
  { title: '项目/产品', slotName: 'project_product', width: 180, ellipsis: true, tooltip: true },
  { title: '模块', dataIndex: 'full_path', width: 240, ellipsis: true, tooltip: true },
  { title: '操作', slotName: 'actions', width: 120, fixed: 'right', align: 'center' },
]
export const overviewModuleScrollX = 1492

export function getInterfaceCoverageData(summary: {
  covered_interface_count: number
  partial_interface_count: number
  uncovered_interface_count: number
  deferred_interface_count: number
}) {
  return [
    { name: '已覆盖', value: summary.covered_interface_count },
    { name: '部分覆盖', value: summary.partial_interface_count },
    { name: '未覆盖', value: summary.uncovered_interface_count },
    { name: '暂不处理', value: summary.deferred_interface_count },
  ]
}

export function getAutomationStatusData(summary: {
  completed_count: number
  target_count: number
  deferred_count: number
}) {
  return [
    { name: '已完成', value: summary.completed_count },
    { name: '未完成', value: Math.max(summary.target_count - summary.completed_count, 0) },
    { name: '暂不处理', value: summary.deferred_count },
  ]
}
