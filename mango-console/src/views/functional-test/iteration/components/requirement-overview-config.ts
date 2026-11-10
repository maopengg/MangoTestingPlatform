import type { TableColumnData } from '@arco-design/web-vue'

export const overviewCaseColumns: TableColumnData[] = [
  { title: '用例编号', dataIndex: 'case_no', width: 130, ellipsis: true, tooltip: true },
  { title: '用例标题', dataIndex: 'title', width: 340, ellipsis: true, tooltip: true },
  { title: '优先级', dataIndex: 'priority', slotName: 'case_priority', width: 90, align: 'center' },
  { title: '负责人', dataIndex: 'owner.name', width: 120, ellipsis: true, tooltip: true },
]
export const overviewPlanColumns: TableColumnData[] = [
  {
    title: '计划名称',
    dataIndex: 'name',
    slotName: 'plan_name',
    width: 440,
    ellipsis: true,
    tooltip: true,
  },
  { title: '状态', dataIndex: 'status', slotName: 'plan_status', width: 100, align: 'center' },
  {
    title: '执行进度',
    dataIndex: 'execution_stats',
    slotName: 'plan_progress',
    width: 110,
    align: 'center',
  },
]
export const overviewDefectColumns: TableColumnData[] = [
  { title: '缺陷编号', dataIndex: 'defect_no', width: 150, ellipsis: true, tooltip: true },
  { title: '缺陷标题', dataIndex: 'title', width: 340, ellipsis: true, tooltip: true },
  { title: '状态', dataIndex: 'status', slotName: 'defect_status', width: 100, align: 'center' },
  { title: '负责人', dataIndex: 'assignee.name', width: 110, ellipsis: true, tooltip: true },
]
