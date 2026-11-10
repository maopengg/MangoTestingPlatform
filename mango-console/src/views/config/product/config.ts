import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'

const table = { indexColumn: { ...useTableIndexColumn(), align: 'center' as const } }

export function createFormItems() {
  return reactive([
    {
      label: '项目名称',
      key: 'project',
      value: ref(''),
      placeholder: '请选择项目名称',
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
      label: 'UI端类型',
      key: 'ui_client_type',
      value: ref(''),
      type: 'select',
      required: true,
      placeholder: '请选择产品的端类型',
      validator: function () {
        if (this.value == null || this.value === '') {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: 'API端类型',
      key: 'api_client_type',
      value: ref(''),
      type: 'select',
      required: true,
      placeholder: '请选择产品的端类型',
      validator: function () {
        if (this.value == null || this.value === '') {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '产品名称',
      key: 'name',
      value: ref(''),
      type: 'input',
      required: true,
      placeholder: '请输入产品名称',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '产品负责人',
      key: 'owners',
      value: ref([]),
      type: 'select',
      multiple: true,
      required: true,
      placeholder: '请选择产品负责人',
      optionItems: [],
      validator: function () {
        if (!Array.isArray(this.value) || this.value.length === 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '产品说明',
      key: 'description',
      value: ref(''),
      type: 'textarea',
      placeholder: '请输入产品用途、Git 仓库地址等信息，请勿填写密码或 Token',
    },
  ])
}
export function createConditionItems() {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入产品ID',
      value: createIdSearchValue(),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'keyword',
      label: '关键字',
      type: 'input',
      placeholder: '搜索项目或产品名称',
      value: ref(''),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'owners',
      label: '产品负责人',
      type: 'select',
      placeholder: '请选择产品负责人',
      value: ref([]),
      multiple: true,
      searchOperator: 'in',
      optionItems: [],
      reset: function () {
        this.value = []
      },
    },
    {
      key: 'ui_client_type',
      label: 'UI类型',
      type: 'select',
      placeholder: '请选择UI产品类型',
      value: ref(''),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'api_client_type',
      label: 'API类型',
      type: 'select',
      placeholder: '请选择API产品类型',
      value: ref(''),
      reset: function () {
        this.value = ''
      },
    },
    createUpdateUserCondition(),
  ]
  return enableMultiSelectSearch(reactive(fields))
}
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '产品名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '产品说明',
    key: 'description',
    dataIndex: 'description',
    align: 'left',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '负责人',
    key: 'owners',
    dataIndex: 'owners',
    width: 110,
  },
  {
    title: 'UI客户端',
    key: 'ui_client_type',
    dataIndex: 'ui_client_type',
    width: 90,
  },
  {
    title: 'API客户端',
    key: 'api_client_type',
    dataIndex: 'api_client_type',
    width: 90,
  },
  { ...updateUserColumn(), key: 'update_user' },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    fixed: 'right',
    width: 160,
  },
])
