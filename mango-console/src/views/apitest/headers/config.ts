import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入ID',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'project_product',
    label: '项目/产品',
    value: ref(''),
    type: 'cascader',
    placeholder: '请选择产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'key',
    label: 'key',
    type: 'input',
    placeholder: '请输入key',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'value',
    label: 'value',
    type: 'input',
    placeholder: '请输入value',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '项目/产品',
    key: 'project_product',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'cascader',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: 'key',
    key: 'key',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入请求头的key',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: 'value',
    key: 'value',
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '请输入key的value值',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 200,
  },
  {
    title: '客户端',
    key: 'client',
    dataIndex: 'client',
    width: 80,
  },
  {
    title: 'key',
    key: 'key',
    dataIndex: 'key',
    align: 'left',
    width: 200,
  },
  {
    title: 'value',
    key: 'value',
    dataIndex: 'value',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '接口管理默认使用',
    key: 'status',
    dataIndex: 'status',
    width: 200,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 110,
  },
])
