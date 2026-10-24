import { reactive } from 'vue'
import { updateUserColumn } from '@/utils/update-user'

export const columns = reactive([
  { title: 'ID', dataIndex: 'id', align: 'center', width: 80 },
  {
    title: '三级模块名称',
    dataIndex: 'level_3_name',
    align: 'left',
    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '二级模块名称',
    dataIndex: 'level_2_name',
    align: 'left',
    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '一级模块名称',
    dataIndex: 'level_1_name',
    align: 'left',
    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  { title: '层级', dataIndex: 'level', align: 'center', width: 90 },
  { title: '创建时间', dataIndex: 'create_time', align: 'center', width: 180 },
  { title: '更新时间', dataIndex: 'update_time', align: 'center', width: 180 },
  updateUserColumn(120),
  { title: '操作', dataIndex: 'actions', align: 'center', fixed: 'right', width: 160 },
])
