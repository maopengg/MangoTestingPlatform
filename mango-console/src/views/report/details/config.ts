import { reactive } from 'vue'

export const uiColumns: any = reactive([
  {
    title: '步骤ID',
    dataIndex: 'id',
    key: 'id',
    width: 120,
  },
  {
    title: '步骤名称',
    dataIndex: 'name',
    key: 'name',
    align: 'left',
    width: 250,
  },
  {
    title: '开始时间',
    dataIndex: 'test_time',
    key: 'test_time',
    width: 170,
  },
  {
    title: '结束时间',
    dataIndex: 'stop_time',
    key: 'stop_time',
    width: 170,
  },
  {
    title: '测试环境',
    dataIndex: 'test_object',
    key: 'test_object',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试结果',
    dataIndex: 'status',
    key: 'status',
    width: 120,
  },
  {
    title: '失败提示',
    dataIndex: 'error_message',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    key: 'actions',
    align: 'center',
    width: 180,
  },
])

export const apiColumns: any = reactive([
  {
    title: '接口ID',
    dataIndex: 'id',
    key: 'id',
    width: 120,
  },
  {
    title: '接口名称',
    dataIndex: 'name',
    key: 'name',
    align: 'left',
    width: 250,
  },

  {
    title: '测试环境',
    dataIndex: 'request_url',
    key: 'request_url',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '开始时间',
    dataIndex: 'test_time',
    key: 'test_time',
    width: 170,
  },
  {
    title: '调用耗时',
    dataIndex: 'response_time',
    key: 'response_time',
    width: 200,
  },
  {
    title: '测试结果',
    key: 'status',
    dataIndex: 'status',
    width: 120,
  },
  {
    title: '失败提示',
    dataIndex: 'error_message',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    key: 'actions',
    align: 'center',
    width: 180,
  },
])
export const pytestColumns: any = reactive([
  {
    title: '用例名称',
    dataIndex: 'name',
    key: 'name',
    align: 'left',
    width: 500,
  },
  {
    title: '开始时间',
    dataIndex: 'start',
    key: 'start',
    width: 170,
  },
  {
    title: '结束时间',
    dataIndex: 'stop',
    key: 'stop',
    width: 170,
  },
  {
    title: '测试结果',
    key: 'status',
    dataIndex: 'status',
    width: 120,
  },
  {
    title: '失败提示',
    dataIndex: 'error_message',
    key: 'error_message',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    key: 'actions',
    align: 'center',
    width: 180,
  },
])
