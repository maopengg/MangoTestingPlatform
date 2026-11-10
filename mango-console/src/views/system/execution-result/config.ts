import { useTable, useTableColumn } from '@/hooks/table'
import type { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive } from 'vue'

const table = useTable()
export const tableScrollX = 2780

export type ExecutionAdminSearchKey = 'id' | 'source_type' | 'target_type' | 'target_id' | 'status' | 'test_env' | 'trigger_user_id' | 'result_state' | 'is_latest' | 'trace_id' | 'create_time'
export interface ExecutionAdminCondition extends Pick<FormItem, 'label' | 'type' | 'placeholder' | 'multiple' | 'searchOperator' | 'reset'> {
  key: ExecutionAdminSearchKey
  value: string | number | boolean | Array<string | number> | null | undefined
}
export function createConditionItems(): ExecutionAdminCondition[] {
  const conditionItems: ExecutionAdminCondition[] = reactive([
    {
      key: 'id',
      label: '记录ID',
      type: 'input',
      placeholder: '请输入记录ID',
      value: createIdSearchValue(),
    },
    {
      key: 'source_type',
      label: '执行来源',
      type: 'select',
      placeholder: '请选择执行来源',
      value: '',
    },
    {
      key: 'target_type',
      label: '对象类型',
      type: 'select',
      placeholder: '请选择对象类型',
      value: '',
    },
    {
      key: 'target_id',
      label: '对象ID',
      type: 'input',
      placeholder: '请输入对象ID',
      value: createIdSearchValue('', false),
    },
    {
      key: 'status',
      label: '执行状态',
      type: 'select',
      placeholder: '请选择执行状态',
      value: [],
      multiple: true,
      searchOperator: 'in',
    },
    {
      key: 'test_env',
      label: '测试环境',
      type: 'select',
      placeholder: '请选择测试环境',
      value: '',
    },
    {
      key: 'trigger_user_id',
      label: '触发人',
      type: 'select',
      placeholder: '请选择触发人',
      value: [],
      multiple: true,
      searchOperator: 'in',
    },
    {
      key: 'result_state',
      label: '结果数据',
      type: 'select',
      placeholder: '请选择结果状态',
      value: '',
    },
    {
      key: 'is_latest',
      label: '结果版本',
      type: 'select',
      placeholder: '请选择结果版本',
      value: '',
    },
    {
      key: 'trace_id',
      label: '链路ID',
      type: 'input',
      placeholder: '请输入链路ID',
      value: '',
    },
    {
      key: 'create_time',
      label: '创建时间',
      type: 'range',
      placeholder: '请选择创建时间',
      value: [],
    },
  ])
  enableMultiSelectSearch(conditionItems)
  return conditionItems
}

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '执行来源',
    key: 'source_type',
    dataIndex: 'source_type',
    width: 110,
  },
  {
    title: '对象类型',
    key: 'target_type',
    dataIndex: 'target_type',
    width: 120,
  },
  {
    title: '对象ID',
    key: 'target_id',
    dataIndex: 'target_id',
    width: 110,
  },
  {
    title: '执行状态',
    key: 'status',
    dataIndex: 'status',
    width: 100,
  },
  {
    title: '测试环境',
    key: 'test_env',
    dataIndex: 'test_env',
    width: 110,
  },
  {
    title: '耗时',
    key: 'duration',
    dataIndex: 'duration',
    width: 100,
  },
  {
    title: '执行次数',
    key: 'attempt_no',
    dataIndex: 'attempt_no',
    width: 90,
  },
  {
    title: '结果版本',
    key: 'is_latest',
    dataIndex: 'is_latest',
    width: 100,
  },
  {
    title: '结果数据',
    key: 'result_state',
    dataIndex: 'result_state',
    width: 110,
  },
  {
    title: '结果大小',
    key: 'result_size',
    dataIndex: 'result_size',
    width: 110,
  },
  {
    title: '触发人',
    key: 'trigger_user_name',
    dataIndex: 'trigger_user_name',
    align: 'left',
    width: 120,
  },
  {
    title: '测试报告ID',
    key: 'test_suite',
    dataIndex: 'test_suite',
    width: 120,
  },
  {
    title: '报告明细ID',
    key: 'test_suite_detail',
    dataIndex: 'test_suite_detail',
    width: 120,
  },
  {
    title: '修订ID',
    key: 'revision_id',
    dataIndex: 'revision_id',
    width: 110,
  },
  {
    title: '发布ID',
    key: 'release_id',
    dataIndex: 'release_id',
    width: 110,
  },
  {
    title: '链路ID',
    key: 'trace_id',
    dataIndex: 'trace_id',
    align: 'left',
    width: 210,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '任务ID',
    key: 'task_id',
    dataIndex: 'task_id',
    align: 'left',
    width: 190,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '错误信息',
    key: 'error_message',
    dataIndex: 'error_message',
    align: 'left',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
])
