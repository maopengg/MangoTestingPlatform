import { createCaseLibraryColumns } from '../case-library/config'
import type { FunctionalGridColumn } from '@/components/table/functional-case-grid'
import type { useEnum } from '@/store/modules/get-enum'
import type { TableColumnData } from '@arco-design/web-vue'

export const emptyPlan = () => ({
  id: undefined,
  name: '',
  project_product: undefined,
  scope_type: 0,
  requirement_version: undefined,
  iteration: undefined,
  scope_ref: '',
  environment: '',
  build_version: '',
  owner: undefined,
  planned_start_time: undefined,
  planned_end_time: undefined,
  status: 0,
  remark: '',
})

export const planColumns: TableColumnData[] = [
  { title: 'ID', dataIndex: 'id', width: 72, align: 'center' },
  {
    title: '计划名称',
    dataIndex: 'name',
    slotName: 'name',
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '计划类型',
    dataIndex: 'scope_type',
    slotName: 'scope_type',
    width: 110,
    align: 'center',
  },
  {
    title: '测试范围',
    dataIndex: 'scope_ref',
    slotName: 'scope_ref',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  { title: '测试环境', dataIndex: 'environment', width: 120, ellipsis: true, tooltip: true },
  { title: '构建版本', dataIndex: 'build_version', width: 120, ellipsis: true, tooltip: true },
  { title: '用例数', dataIndex: 'case_count', width: 90, align: 'center' },
  { title: '执行进度', dataIndex: 'execution_stats', slotName: 'execution_progress', width: 180 },
  {
    title: '通过率',
    dataIndex: 'execution_stats',
    slotName: 'pass_rate',
    width: 110,
    align: 'center',
  },
  { title: '未关闭缺陷', dataIndex: 'open_defect_count', width: 110, align: 'center' },
  { title: '未提缺陷', dataIndex: 'unlinked_failed_count', width: 100, align: 'center' },
  {
    title: '负责人',
    dataIndex: 'owner',
    slotName: 'owner',
    width: 110,
    ellipsis: true,
    tooltip: true,
  },
  { title: '状态', dataIndex: 'status', slotName: 'status', width: 100, align: 'center' },
  { title: '更新时间', dataIndex: 'update_time', width: 165 },
  {
    title: '项目/产品',
    dataIndex: 'project_product',
    slotName: 'project_product',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  { title: '操作', slotName: 'actions', fixed: 'right', width: 140, align: 'center' },
]

const RESULT_COLOR_TOKENS: Record<string, string> = {
  0: '--m-muted',
  1: '--m-success',
  2: '--m-danger',
  3: '--m-warning',
  4: '--m-chart-5',
}

export const createPlanCaseColumns = (
  enums: Parameters<typeof createCaseLibraryColumns>[0] &
    Pick<ReturnType<typeof useEnum>, 'functional_test_result'>,
  users: Parameters<typeof createCaseLibraryColumns>[1] = []
): FunctionalGridColumn[] => [
  ...createCaseLibraryColumns(enums, users),
  { field: 'defect_summary', title: '关联缺陷', width: 240, editable: false },
  { field: 'open_defect_count', title: '未关闭缺陷', width: 110, editable: false, align: 'center' },
  { field: 'actual_result', title: '实际结果', width: 220, editor: 'textarea' },
  { field: 'execution_note', title: '执行备注', width: 180, editor: 'textarea' },
  {
    field: 'result',
    title: '本次结果',
    width: 110,
    fixed: 'right',
    align: 'center',
    options: (enums.functional_test_result || []).map((item) => ({
      label: item.title,
      value: item.key,
      colorToken: RESULT_COLOR_TOKENS[String(item.key)] || '--m-primary',
    })),
  },
]
