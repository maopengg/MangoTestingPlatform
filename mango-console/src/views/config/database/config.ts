import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
const table = useTable()
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入数据库ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
])
export const formItems: FormItem[] = reactive([
  {
    label: '项目名称',
    key: 'project',
    value: '',
    placeholder: '请选择项目名称',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '绑定环境',
    key: 'test_obj',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请选择对应环境',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '域名',
    key: 'host',
    value: '',
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
    value: '',
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
    value: '',
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
    value: '',
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
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 150,
  },
  {
    title: '对应环境',
    key: 'test_obj',
    dataIndex: 'test_obj',
    align: 'left',
  },
  {
    title: '域名',
    key: 'host',
    dataIndex: 'host',
    align: 'left',
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
    width: 150,
  },
])
