import { reactive } from 'vue'

import type { FormItem } from '@/types/components'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { enableMultiSelectSearch } from '@/utils/search-condition'

export const tableScrollX = 1650

export interface FireRecordOption { label: string; value: number }

export const fireStatusOptions: FireRecordOption[] = [
  { label: '待分发', value: 0 },
  { label: '分发中', value: 1 },
  { label: '已分发', value: 2 },
  { label: '成功', value: 3 },
  { label: '失败', value: 4 },
  { label: '已跳过', value: 5 },
  { label: '已取消', value: 6 },
]

export const fireSourceTypeOptions: FireRecordOption[] = [
  { label: '测试套执行', value: 0 },
  { label: 'Token刷新', value: 1 },
  { label: '数据清理', value: 2 },
  { label: '监控任务', value: 3 },
  { label: '系统定时任务', value: 4 },
]

export interface FireRecordCondition extends Pick<FormItem, 'label' | 'type' | 'placeholder' | 'multiple' | 'searchOperator' | 'reset'> {
  key: 'task_name' | 'status' | 'source_type'
  value: string | number | Array<string | number> | null | undefined
  optionItems?: FireRecordOption[]
}
export function createConditionItems(): FireRecordCondition[] {
  const conditionItems: FireRecordCondition[] = [
    {
      key: 'task_name',
      label: '任务名称',
      type: 'input',
      placeholder: '请输入任务名称',
      value: '',
      optionItems: [],
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'status',
      label: '状态',
      type: 'select',
      placeholder: '请选择状态',
      value: '',
      optionItems: fireStatusOptions.map(item => ({ ...item })),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'source_type',
      label: '触发类型',
      type: 'select',
      placeholder: '请选择触发类型',
      value: '',
      optionItems: fireSourceTypeOptions.map(item => ({ ...item })),
      reset: function () {
        this.value = ''
      },
    },
  ]
  enableMultiSelectSearch(conditionItems)
  return reactive(conditionItems)
}

export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '任务名称',
    key: 'task_name',
    dataIndex: 'task_name',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '定时策略',
    key: 'time_task',
    dataIndex: 'time_task',
    align: 'left',
    width: 160,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '触发类型',
    key: 'source_type',
    dataIndex: 'source_type',
    width: 110,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 100,
  },
  {
    title: '计划时间',
    key: 'planned_at',
    dataIndex: 'planned_at',
    width: 180,
  },
  {
    title: '触发时间',
    key: 'fired_at',
    dataIndex: 'fired_at',
    width: 180,
  },
  {
    title: '触发节点',
    key: 'trigger_node',
    dataIndex: 'trigger_node',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '分发节点',
    key: 'dispatcher_node',
    dataIndex: 'dispatcher_node',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '错误信息',
    key: 'error_message',
    dataIndex: 'error_message',
    align: 'left',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
