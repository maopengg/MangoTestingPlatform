import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '测试类型',
    key: 'type',
    dataIndex: 'type',
  },
  {
    title: '用例名称',
    key: 'case_id',
    dataIndex: 'case_id',
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
    label: '测试类型',
    key: 'type',
    value: 0,
    placeholder: '请选择自动化类型',
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
    label: '模块名称',
    key: 'module',
    value: ref(''),
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
    key: 'case_id',
    value: ref(''),
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