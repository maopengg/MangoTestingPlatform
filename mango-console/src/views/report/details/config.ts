import { reactive } from 'vue'

export const uiColumns: any = reactive([
  {
    title: '产品名称',
    dataIndex: 'project_product_name',
  },
  {
    title: '步骤名称',
    dataIndex: 'name',
  },
  {
    title: '测试时间',
    dataIndex: 'test_time',
  },
  {
    title: '测试环境',
    dataIndex: 'test_object',
  },
  {
    title: '测试结果',
    dataIndex: 'status',
  },
  {
    title: '失败提示',
    dataIndex: 'error_message',
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 180,
  },
])

export const apiColumns: any = reactive([
  {
    title: '产品名称',
    dataIndex: 'project_product_name',
  },
  {
    title: '接口名称',
    dataIndex: 'name',
  },

  {
    title: '测试环境',
    dataIndex: 'request_url',
  },
  {
    title: '耗时',
    dataIndex: 'response_time',
  },
  {
    title: '测试结果',
    dataIndex: 'status',
  },
  {
    title: '失败提示',
    dataIndex: 'error_message',
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 180,
  },
])
export const pytestColumns: any = reactive([
  {
    title: '用例名称',
    dataIndex: 'name',
  },
  {
    title: '开始时间',
    dataIndex: 'start',
  },
  {
    title: '结束时间',
    dataIndex: 'test_time',
  },
  {
    title: '测试结果',
    dataIndex: 'status',
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 180,
  },
])
