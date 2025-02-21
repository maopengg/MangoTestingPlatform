import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const formItems: FormItem[] = reactive([
  {
    label: '项目/产品',
    key: 'project_product',
    value: ref(''),
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
    label: '名称',
    key: 'name',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value && this.value !== '0') {
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
    title: '项目目录名称',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '文件名称',
    key: 'file_name',
    dataIndex: 'file_name',
  },

  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 190,
  },
])
