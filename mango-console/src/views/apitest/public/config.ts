import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'

const table = useTable()
export const tableScrollX = 2080

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入参数ID',
    value: createIdSearchValue(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'project_product',
    label: '项目/产品',
    value: ref(''),
    type: 'cascader',
    placeholder: '请选择产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'type',
    label: '类型',
    value: ref(''),
    type: 'select',
    placeholder: '请选择类型',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'test_envs',
    label: '被测环境',
    value: ref([]),
    type: 'select',
    placeholder: '请选择被测环境',
    optionItems: [],
    reset: function () {
      this.value = []
    },
  },
  {
    key: 'status',
    label: '默认开启',
    value: ref([]),
    type: 'select',
    placeholder: '请选择开启状态',
    optionItems: [
      { key: 1, title: '开启' },
      { key: 0, title: '关闭' },
    ],
    reset: function () {
      this.value = []
    },
  },
  createUpdateUserCondition(),
  {
    key: 'name',
    label: '参数名称',
    type: 'input',
    placeholder: '请输入参数名称',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'key',
    label: 'key',
    type: 'input',
    placeholder: '请输入key',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'value',
    label: 'value',
    type: 'input',
    placeholder: '请输入value',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
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
    label: '类型',
    key: 'type',
    value: ref(''),
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
    label: '被测环境',
    key: 'test_envs',
    value: ref(''),
    type: 'select',
    required: false,
    placeholder: '请选择被测环境',
    validator: function () {
      return true
    },
    reset: function () {
      this.value = ''
    },
  },
  {
    label: '参数名称',
    key: 'name',
    value: ref(''),
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
    value: ref(''),
    type: 'input',
    required: true,
    placeholder:
      '请输入缓存key；SQL变量多值可用英文逗号分隔，如 id,name；代码变量key仅作标识，不参与变量注入',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '逻辑数据库',
    key: 'datasource_alias',
    value: ref(''),
    type: 'select',
    required: false,
    placeholder: '请选择逻辑数据库',
    reset: function () {
      this.value = ''
    },
  },
  {
    label: 'value',
    key: 'value',
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '自定义变量请输入变量值，SQL变量请输入查询一行数据的语句',
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
    title: '被测环境',
    key: 'test_env',
    dataIndex: 'test_env',
    width: 120,
  },
  {
    title: '类型',
    key: 'type',
    dataIndex: 'type',
    width: 150,
  },
  {
    title: '参数名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 200,
  },
  {
    title: 'key',
    key: 'key',
    dataIndex: 'key',
    align: 'left',
    width: 300,
  },
  {
    title: 'value',
    key: 'value',
    dataIndex: 'value',
    align: 'left',
    width: 320,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '默认开启',
    key: 'status',
    dataIndex: 'status',
    width: 90,
  },
  {
    title: '逻辑数据库',
    key: 'datasource_alias',
    dataIndex: 'datasource_alias',
    align: 'left',
    width: 160,
  },
  updateUserColumn(),
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
  },
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
