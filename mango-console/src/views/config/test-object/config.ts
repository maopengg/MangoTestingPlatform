import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateTimeColumn, updateUserColumn } from '@/utils/update-user'

const table = useTable()
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入测试对象ID',
    value: createIdSearchValue(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '环境名称',
    type: 'input',
    placeholder: '请输入环境名称',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'project_product',
    label: '项目/产品',
    type: 'cascader',
    placeholder: '请选择项目/产品',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'environment',
    label: '部署环境',
    value: ref(''),
    type: 'select',
    placeholder: '请选择部署环境',
    optionItems: [],
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'auto_type',
    label: '自动化类型',
    value: ref(''),
    type: 'select',
    placeholder: '请选择自动化类型',
    optionItems: [],
    reset: function () {
      this.value = ''
    },
  },
  createUpdateUserCondition(),
])
enableMultiSelectSearch(conditionItems)
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
    label: '环境名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入环境名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '被测环境',
    key: 'environment',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择绑定环境',
    validator: function () {
      if (this.value === null && this.value === '') {
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
    type: 'select',
    required: true,
    placeholder: '请选择产品的端类型',
    validator: function () {
      if (this.value === null && this.value === '') {
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
    title: '环境名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '域名/包名/路径',
    key: 'value',
    dataIndex: 'value',
    align: 'left',
    width: 400,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '部署环境',
    key: 'environment',
    dataIndex: 'environment',
    width: 100,
  },
  {
    title: '自动化类型',
    key: 'auto_type',
    dataIndex: 'auto_type',
    width: 130,
  },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  updateUserColumn(),
  updateTimeColumn(),
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
