import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

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
    placeholder: '请输入接口名称',
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
    placeholder: '请输入url',
    reset: function () {},
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
    key: 'module',
    label: '模块名称',
    value: ref(''),
    type: 'select',
    placeholder: '请选择模块',
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
    placeholder: '请输入url后面的路径',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      if (this.value.toLowerCase().startsWith('http')) {
        Message.error('只允许输入url的路径部分，协议和域名部分从测试环境中读取！')
        return false
      }
      return true
    },
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
    placeholder: '请输入复制的cURL（bash）',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      const cmd = this.value.trim()
      const isBrowserCurl =
        cmd.startsWith('curl ') &&
        (cmd.includes("'") || cmd.includes('"')) &&
        !cmd.includes('^"') &&
        cmd.includes(' \\\n') &&
        !cmd.includes(' ^\n') &&
        (cmd.includes('--compressed') || cmd.includes('--insecure') || cmd.includes('User-Agent:'))
      if (!isBrowserCurl) {
        Message.error('请从浏览器开发者工具(F12)中复制 cURL (base)，不要手动输入！')
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
    width: 160,
  },
])
