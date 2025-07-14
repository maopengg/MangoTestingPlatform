import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()
import parseCurl from 'parse-curl'

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入接口ID',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },

  {
    key: 'name',
    label: '接口名称',
    type: 'input',
    placeholder: '请输入用例名称',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'url',
    label: 'url',
    value: ref(''),
    type: 'input',
    placeholder: '请选择产品',
    reset: function () {},
  },
  {
    key: 'project_product',
    label: '产品',
    value: ref(''),
    type: 'select',
    placeholder: '请选择产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'module',
    label: '模块',
    value: ref(''),
    type: 'select',
    placeholder: '请选择产品',
    optionItems: [],
    reset: function () {},
  },
  {
    key: 'status',
    label: '状态',
    value: ref(''),
    type: 'select',
    placeholder: '请选择步骤状态',
    optionItems: [],
    reset: function () {},
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
    label: '模块名称',
    key: 'module',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请用例归属模块',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '接口名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入用例名称',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },

  {
    label: 'url',
    key: 'url',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入url',
  },
  {
    label: 'method',
    key: 'method',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择接口方法',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
export const formItemsImport: FormItem[] = reactive([
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
    type: 'select',
    required: true,
    placeholder: '请用例归属模块',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '接口名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入用例名称',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: 'curl',
    key: 'curl_command',
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '请输入复制的curl（bash）',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      // const parsedCurl = parseCurl(this.value)
      // const dataRaw = parseDataRaw(this.value)
      // this.value = { ...parsedCurl, data: dataRaw }
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
    width: 200,
  },
  {
    title: '模块名称',
    key: 'module',
    dataIndex: 'module',
    align: 'left',
    width: 180,
  },
  {
    title: '接口名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 300,
  },
  {
    title: '端类型',
    key: 'client',
    dataIndex: 'client',
    width: 80,
  },
  {
    title: 'url',
    key: 'url',
    dataIndex: 'url',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '方法',
    key: 'method',
    dataIndex: 'method',
    width: 70,
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
    width: 180,
  },
])
