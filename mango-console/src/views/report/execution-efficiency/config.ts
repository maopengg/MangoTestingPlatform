import type { TableColumnData } from '@arco-design/web-vue'
import type { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import type { EfficiencyId, EfficiencyOption } from './overview'

export type TaskOptionKey = 'task_ids' | 'task_group_ids'
export type EfficiencySearchKey = 'test_env' | 'case_type' | TaskOptionKey | 'report_id'
type ConditionBase = Omit<FormItem, 'key' | 'value' | 'type' | 'optionItems'> & { optionItems: EfficiencyOption[] }
export type EfficiencyCondition = ConditionBase & (
  { key: Exclude<EfficiencySearchKey, 'report_id'>; type: 'select'; value: EfficiencyId[] }
  | { key: 'report_id'; type: 'input'; value: string }
)

export const sectionOptions = [
  { value: 'queue', label: '当前排队' }, { value: 'timing', label: 'API 耗时分析' },
  { value: 'anomalies', label: '异常线索' },
]
export const rankingOptions = [{ value: 'cases', label: '慢 Case' }, { value: 'reports', label: '慢报告' }]
export function createConditions(): EfficiencyCondition[] {
  const items: EfficiencyCondition[] = [
    { key: 'test_env', label: '被测环境', type: 'select', value: [], optionItems: [] },
    { key: 'case_type', label: '自动化类型', type: 'select', value: [], optionItems: [
      { value: 0, label: 'UI自动化' }, { value: 1, label: 'API自动化' }, { value: 2, label: 'Pytest自动化' },
    ] },
    { key: 'task_ids', label: '定时任务', type: 'select', value: [], optionItems: [] },
    { key: 'task_group_ids', label: '任务组', type: 'select', value: [], optionItems: [] },
    { key: 'report_id', label: '执行报告ID', type: 'input', value: '', placeholder: '请输入执行报告ID', optionItems: [] },
  ]
  enableMultiSelectSearch(items)
  return items
}
const col = (title: string, dataIndex: string, width: number, align: 'left' | 'center' = 'center'): TableColumnData =>
  ({ title, dataIndex, slotName: dataIndex, width, align, ellipsis: true, tooltip: true })
const ownership: TableColumnData[] = [
  { title: '项目/产品', dataIndex: 'project_product', slotName: 'project_product', width: 160, align: 'left', ellipsis: true, tooltip: true },
  { title: '模块', dataIndex: 'module', slotName: 'module', width: 140, align: 'left', ellipsis: true, tooltip: true },
]
export const queueColumns: TableColumnData[] = [
  col('执行报告ID', 'report_id', 165), col('任务名称', 'name', 220, 'left'),
  col('被测环境', 'test_env', 100), col('待开始', 'pending', 75), col('执行中', 'running', 75),
  col('已完成', 'completed', 75), col('API并发', 'limit', 100), col('最长等待', 'wait', 110),
  col('当前最长执行项', 'current', 260, 'left'), col('排队诊断', 'diagnosis', 230, 'left'),
  ...ownership, { ...col('操作', 'actions', 160), fixed: 'right' },
]
export const anomalyColumns: TableColumnData[] = [
  col('执行报告ID', 'report_id', 165), col('任务名称', 'report_name', 200, 'left'),
  col('用例名称', 'case_name', 240, 'left'), col('被测环境', 'test_env', 100),
  col('当前阶段', 'stage', 180, 'left'), col('执行耗时', 'elapsed', 100),
  col('异常线索', 'reason', 280, 'left'), ...ownership,
  { ...col('操作', 'actions', 160), fixed: 'right' },
]
export const slowCaseColumns: TableColumnData[] = [
  col('用例名称', 'case_name', 300, 'left'), col('执行报告ID', 'report_id', 165),
  col('开始时间', 'started_at', 170),
  col('单次耗时', 'duration', 110), col('主要耗时阶段', 'dominant_phase', 150, 'left'),
  ...ownership,
  { ...col('操作', 'actions', 160), fixed: 'right' },
]
export const slowReportColumns: TableColumnData[] = [
  col('任务名称', 'name', 280, 'left'), col('执行报告ID', 'report_id', 165),
  col('API执行跨度', 'span', 140), col('首个已采集启动延迟', 'delay', 170),
  col('计时状态', 'timing_status', 140), ...ownership, { ...col('操作', 'actions', 160), fixed: 'right' },
]
export const efficiencyScrollWidths = Object.fromEntries(
  Object.entries({ queue: queueColumns, anomalies: anomalyColumns, cases: slowCaseColumns, reports: slowReportColumns })
    .map(([key, columns]) => [key, columns.reduce((width, column) => width + Number(column.width || 0), 0)])
)
export function duration(value: unknown): string {
  if ((typeof value !== 'number' && !(typeof value === 'string' && /^\d+(\.\d+)?$/.test(value))) || !Number.isFinite(Number(value)) || Number(value) < 0) return '—'
  const ms = Number(value)
  if (ms < 1000) return `${Math.round(ms)} ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(2)} 秒`
  return `${Math.floor(ms / 60000)}分${Math.floor((ms % 60000) / 1000)}秒`
}

export function compactTableHeight(rows: number) {
  return Math.min(260, Math.max(60, rows * 36 + 4))
}

export function diagnosisTone(value: string) {
  if (value === '未检测到在线 API Worker') return 'danger'
  if (value === '报告并发限制' || value === '当前执行容量繁忙' || value.startsWith('持续等待')) return 'warning'
  return 'neutral'
}
