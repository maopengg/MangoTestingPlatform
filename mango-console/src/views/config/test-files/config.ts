import { useTable, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'

const table = useTable()

export const tableScrollX = 1370

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入ID',
    value: createIdSearchValue(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '文件名称',
    type: 'input',
    placeholder: '请输入文件名称',
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
    placeholder: '请选择项目/产品',
    optionItems: [],
    reset: function () {},
  },
  createUpdateUserCondition(),
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
])

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '文件名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 280,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '文件大小',
    key: 'file_size',
    dataIndex: 'file_size',
    width: 110,
  },
  {
    title: '下载权限',
    key: 'allow_download',
    dataIndex: 'allow_download',
    width: 110,
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
  },
  updateUserColumn(),
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
