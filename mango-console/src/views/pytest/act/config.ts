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
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '模块',
    key: 'module',
    value: ref(''),
    placeholder: '请选择模块名称',
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
    label: '名称',
    key: 'name',
    value: ref(''),
    placeholder: '请输入名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '绑定状态',
    key: 'file_status',
    value: ref(''),
    placeholder: '请选择绑定状态',
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
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 180,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
    width: 180,
  },
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
  },
  {
    title: '文件名称',
    key: 'file_name',
    dataIndex: 'file_name',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 250,
  },
  {
    title: '修改时间',
    key: 'file_update_time',
    dataIndex: 'file_update_time',
    width: 170,
  },
  {
    title: '文件状态',
    key: 'file_status',
    dataIndex: 'file_status',
    width: 90,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 190,
  },
])
