import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '参数名称',
    type: 'input',
    placeholder: '请输入参数名称',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'client',
    label: '客户端',
    value: '',
    type: 'select',
    placeholder: '选择客户端类型',
    optionItems: [],
    reset: function () {},
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '项目/产品',
    key: 'project_product',
    value: '',
    placeholder: '请选择项目名称',
    required: true,
    type: 'cascader',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '客户端',
    key: 'client',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请选择客户端',
    validator: function () {
      // @ts-ignore
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '类型',
    key: 'type',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请选择对应类型，注意不同类型的加载顺序',
    validator: function () {
      // @ts-ignore
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '参数名称',
    key: 'name',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: 'key',
    key: 'key',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入缓存的key',
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
    value: '',
    type: 'textarea',
    required: true,
    placeholder: '请根据规则输入value值',
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
    width: 180,
  },
  {
    title: '客户端',
    key: 'client',
    dataIndex: 'client',
    width: 80,
  },
  {
    title: '类型',
    key: 'type',
    dataIndex: 'type',
    width: 70,
  },
  {
    title: '参数名称',
    key: 'name',
    dataIndex: 'name',
    width: 200,
  },
  {
    title: 'key',
    key: 'key',
    dataIndex: 'key',
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
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 70,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
