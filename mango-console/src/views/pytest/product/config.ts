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
    label: '名称',
    key: 'name',
    value: ref(''),
    placeholder: '请选择名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '自动化类型',
    key: 'auto_type',
    value: ref(''),
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
    label: '测试目录',
    key: 'test_dir',
    value: ref([]),
    placeholder: '请输入测试文件所在目录名称，回车输入多个',
    required: true,
    type: 'input-tag',
    validator: function () {
      if (!this.value || this.value.length === 0) {
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
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 300,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '文件名称',
    key: 'file_name',
    dataIndex: 'file_name',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '自动化类型',
    key: 'auto_type',
    dataIndex: 'auto_type',
    width: 120,
  },
  {
    title: '测试文件目录',
    key: 'test_dir',
    dataIndex: 'test_dir',
    width: 300,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 180,
  },
])
