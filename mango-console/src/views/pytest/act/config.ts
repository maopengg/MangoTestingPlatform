import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const formItems: FormItem[] = reactive([
  {
    label: '项目/产品',
    key: 'pytest_project',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'select',
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
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'select',
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
    placeholder: '请输入模块名称',
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
])
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目/产品',
    key: 'pytest_project',
    dataIndex: 'pytest_project',
    width: 180,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
  },
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '文件名称',
    key: 'file_name',
    dataIndex: 'file_name',
  },
  {
    title: '修改时间',
    key: 'file_update_time',
    dataIndex: 'file_update_time',
  },
  {
    title: '文件状态',
    key: 'file_status',
    dataIndex: 'file_status',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 190,
  },
])
