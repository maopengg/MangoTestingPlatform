import { reactive } from 'vue'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import type { FormItem } from '@/types/components'
import { useTableColumn } from '@/hooks/table'

export const tableScrollX = 1540

export const categoryOptions = [
  { key: 'system_error_event', title: '系统异常事件' },
  { key: 'schedule_fire', title: '调度触发失败' },
]

export const sourceTagOptions = [
  { key: 'http', title: '接口异常' },
  { key: 'frontend', title: '前端异常' },
  { key: 'actuator', title: '执行器异常' },
  { key: 'scheduler', title: '调度服务异常' },
  { key: 'api-worker', title: 'API Worker异常' },
  { key: 'mcp', title: 'MCP服务异常' },
  { key: 'realtime', title: '实时服务异常' },
  { key: 'monitoring', title: '监控服务异常' },
  { key: 'performance', title: '性能任务异常' },
  { key: 'schedule_fire', title: '调度触发失败' },
]

export interface ErrorRecordCondition extends Pick<FormItem, 'label' | 'type' | 'placeholder' | 'multiple' | 'searchOperator' | 'reset'> {
  key: 'category' | 'keyword' | 'source'
  value: string | string[]
  optionItems?: Array<{ label: string; value: string }>
}

export function createConditionItems(): ErrorRecordCondition[] {
  const conditionItems: ErrorRecordCondition[] = [
    {
      key: 'category',
      label: '记录类型',
      type: 'select',
      placeholder: '请选择记录类型',
      value: '',
      optionItems: categoryOptions.map((item) => ({ label: item.title, value: item.key })),
    },
    {
      key: 'keyword',
      label: '异常关键字',
      type: 'input',
      placeholder: '搜索对象、异常类型或错误摘要',
      value: '',
    },
    {
      key: 'source',
      label: '来源',
      type: 'select',
      placeholder: '请选择异常来源',
      value: [],
      multiple: true,
      optionItems: sourceTagOptions.map((item) => ({
        label: item.title,
        value: item.key === 'http' ? 'http,drf' : item.key,
      })),
    },
  ]
  // The aggregate endpoint uses category=scalar and source=comma-list, not __in.
  enableMultiSelectSearch(conditionItems, ['category'])
  return reactive(conditionItems)
}

export const tableColumns = useTableColumn([
  { title: '时间', key: 'time', dataIndex: 'time', width: 180 },
  { title: '来源', key: 'source_name', dataIndex: 'source_name', width: 130 },
  {
    title: '对象',
    key: 'title',
    dataIndex: 'title',
    align: 'left',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '异常类型',
    key: 'exception_type',
    dataIndex: 'exception_type',
    width: 160,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '错误摘要',
    key: 'message',
    dataIndex: 'message',
    align: 'left',
    width: 460,
    ellipsis: true,
    tooltip: true,
  },
  { title: '出现次数', key: 'count', dataIndex: 'count', width: 100 },
  { title: '状态', key: 'status_name', dataIndex: 'status_name', width: 90 },
  { title: '操作', key: 'actions', dataIndex: 'actions', fixed: 'right', width: 160 },
])
