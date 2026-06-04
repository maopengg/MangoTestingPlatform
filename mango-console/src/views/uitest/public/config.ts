import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const conditionItems: FormItem[] = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入参数ID',
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
    placeholder: '请选择产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'test_env',
    label: '环境',
    value: ref(''),
    type: 'select',
    placeholder: '请选择环境',
    optionItems: [],
    reset: function () {
      this.value = ''
    },
  },
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
  {
    label: '类型',
    key: 'type',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择对应类型，注意不同类型的加载顺序',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '环境',
    key: 'test_env',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择绑定环境',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
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
      if (!this.value && this.value !== 0) {
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
    placeholder: '请输入缓存的key,sql则使用逗号隔开保存多个key',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '逻辑数据源',
    key: 'datasource_alias',
    value: ref(''),
    type: 'select',
    required: false,
    placeholder: '请选择逻辑数据源',
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
    placeholder: '请根据规则输入value值',
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
    align: 'left',
    width: 150,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '环境',
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
    width: 200,
  },
  {
    title: '逻辑数据源',
    key: 'datasource_alias',
    dataIndex: 'datasource_alias',
    align: 'left',
    width: 160,
  },
  {
    title: 'value',
    key: 'value',
    dataIndex: 'value',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 70,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 170,
  },
])
