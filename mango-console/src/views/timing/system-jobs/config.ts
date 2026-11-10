import { reactive } from 'vue'
import type { FormItem } from '@/types/components'
import { useTableColumn } from '@/hooks/table'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { fireSourceTypeOptions, fireStatusOptions } from '@/views/system/fire-record/config'

export const tableScrollX = 2200
export function createConditionItems(): FormItem[] {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
    { key: 'key', label: '任务标识', type: 'input', value: '', placeholder: '请输入任务标识' },
    { key: 'name', label: '任务名称', type: 'input', value: '', placeholder: '请输入任务名称' },
    { key: 'description', label: '任务说明', type: 'input', value: '', placeholder: '请输入任务说明' },
    { key: 'cron', label: 'Cron', type: 'input', value: '', placeholder: '请输入 Cron 表达式' },
    { key: 'source_type', label: '触发类型', type: 'select', value: [], placeholder: '请选择触发类型', optionItems: fireSourceTypeOptions.map(item => ({ ...item })) },
    { key: 'latest_status', label: '最近状态', type: 'select', value: [], placeholder: '请选择最近状态',
      optionItems: [...fireStatusOptions.map(item => ({ ...item })), { label: '尚未触发', value: 'untriggered' }] },
    { key: 'latest_error_message', label: '最近错误', type: 'input', value: '', placeholder: '请输入最近错误' },
  ]
  const items = enableMultiSelectSearch(reactive(fields))
  for (const item of items) item.reset = function () { this.value = this.multiple ? [] : '' }
  return items
}
export const tableColumns = useTableColumn([
  { title: '任务标识', key: 'index', dataIndex: 'index', align: 'left', width: 190, ellipsis: true, tooltip: true },
  { title: '任务名称', key: 'name', dataIndex: 'name', align: 'left', width: 180, ellipsis: true, tooltip: true },
  { title: '任务说明', key: 'description', dataIndex: 'description', align: 'left', width: 560, ellipsis: true, tooltip: true },
  { title: 'Cron', key: 'cron', dataIndex: 'cron', width: 130, ellipsis: true, tooltip: true },
  { title: '触发类型', key: 'source_type', dataIndex: 'source_type', width: 110 },
  { title: '下次触发时间', key: 'next_fire_at', dataIndex: 'next_fire_at', width: 180 },
  { title: '最近状态', key: 'latest_status', dataIndex: 'latest_status', width: 110 },
  { title: '最近计划时间', key: 'latest_planned_at', dataIndex: 'latest_planned_at', width: 180 },
  { title: '最近触发时间', key: 'latest_fired_at', dataIndex: 'latest_fired_at', width: 180 },
  { title: '最近错误', key: 'latest_error_message', dataIndex: 'latest_error_message', align: 'left', width: 220, ellipsis: true, tooltip: true },
  { title: '操作', key: 'actions', dataIndex: 'actions', fixed: 'right', width: 160 },
])
