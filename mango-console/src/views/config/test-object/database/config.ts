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
    placeholder: '请输入数据库ID',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
])
export const formItems: FormItem[] = reactive([
  {
    label: '逻辑数据源',
    key: 'datasource_alias',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择逻辑数据源',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '数据库类型',
    key: 'db_type',
    value: 0,
    type: 'select',
    required: true,
    placeholder: '请选择数据库类型',
    validator: function () {
      if (this.value === null || this.value === undefined || this.value === '') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '域名',
    key: 'host',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入数据库域名',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '端口',
    key: 'port',
    value: '3306',
    type: 'input',
    required: true,
    placeholder: '请输入数据库端口',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '主库',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入主库名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '用户名',
    key: 'user',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入用户名',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '密码',
    key: 'password',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入密码',
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
    title: '域名',
    key: 'host',
    dataIndex: 'host',
    align: 'left',
  },
  {
    title: '类型',
    key: 'db_type',
    dataIndex: 'db_type',
    width: 120,
  },
  {
    title: '端口',
    key: 'port',
    dataIndex: 'port',
    width: 130,
  },
  {
    title: '主库',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '绑定逻辑数据源',
    key: 'datasource_alias',
    dataIndex: 'datasource_alias',
    width: 180,
  },
  {
    title: '用户名',
    key: 'user',
    dataIndex: 'user',
    width: 130,
  },
  {
    title: '密码',
    key: 'password',
    dataIndex: 'password',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 170,
  },
])
