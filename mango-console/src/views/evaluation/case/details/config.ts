export const itemColumns = [
  { title: '条目 ID', dataIndex: 'dataset_item_id', width: 100, align: 'center' }, { title: '重复', dataIndex: 'repeat_index', width: 75, align: 'center' },
  { title: '调用状态', slotName: 'executionStatus', width: 110, align: 'center' }, { title: '评分状态', slotName: 'gradeStatus', width: 110, align: 'center' },
  { title: '效果结论', slotName: 'verdict', width: 100, align: 'center' }, { title: '得分', dataIndex: 'score', width: 90, align: 'center' },
  { title: '执行耗时', slotName: 'duration', width: 110, align: 'center' }, { title: '错误信息', slotName: 'error', width: 250, ellipsis: true, tooltip: true },
  { title: '操作', slotName: 'actions', width: 160, fixed: 'right', align: 'center' },
]
export const gradingColumns = [
  { title: '评分器与版本', slotName: 'graders', width: 220, ellipsis: true, tooltip: true },
  { title: '通过阈值', slotName: 'thresholds', width: 100, align: 'center' },
  { title: '权重', slotName: 'weights', width: 80, align: 'center' },
  { title: '计分方式', slotName: 'gradingModes', width: 110, align: 'center' },
]
export const unexecutedColumns = [
  itemColumns[0],
  ...gradingColumns,
  { title: '测试状态', slotName: 'unexecuted', width: 100, align: 'center' },
]
