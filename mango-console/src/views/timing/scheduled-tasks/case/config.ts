import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '任务名称',
    key: 'task',
    dataIndex: 'task',
    width: 200,
  },
  {
    title: '用例名称',
    key: 'case',
    dataIndex: 'case',
  },
  {
    title: '执行排序',
    key: 'sort',
    dataIndex: 'sort',
  },
  {
    title: '用例绑定环境',
    key: 'test_object',
    dataIndex: 'test_object',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 130,
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
    label: '模块',
    key: 'module',
    value: '',
    placeholder: '请选择测试模块',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '用例名称',
    key: 'case',
    value: '',
    placeholder: '请选择用例名称',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
