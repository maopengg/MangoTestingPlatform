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
    placeholder: '请输入用户ID',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'nickname',
    label: '昵称',
    type: 'input',
    placeholder: '请输入昵称',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'username',
    label: '账号',
    type: 'input',
    placeholder: '请输入账号',
    value: '',
    reset: function () {
      this.value = ''
    },
  },
])
export const formItems: FormItem[] = reactive([
  {
    label: '昵称',
    key: 'nickname',
    value: '',
    placeholder: '请输入用户昵称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '账号',
    key: 'username',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入用户账号',
    validator: function () {
      if (!this.value && this.value !== '0') {
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
    required: false,
    placeholder: '请输入用户密码',
    validator: function () {
      // 判断value是否包含汉字
      const reg = new RegExp('[\\u4E00-\\u9FFF]+', 'g')
      if (reg.test(this.value)) {
        Message.error('不能输入汉字')
        return false
      }
      return true
    },
  },
  {
    label: '绑定角色',
    key: 'role',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请选择用户角色',
    validator: function () {
      if (this.value === null && this.value === '') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '邮箱',
    key: 'mailbox',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入邮箱',
    validator: function () {
      if (!this.value && this.value !== '0') {
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
    title: '昵称',
    key: 'nickname',
    dataIndex: 'nickname',
    width: 150,
  },
  {
    title: '账号',
    key: 'username',
    dataIndex: 'username',
    align: 'left',
  },
  {
    title: '角色',
    key: 'role',
    dataIndex: 'role',
  },
  {
    title: '最近登录时间',
    key: 'last_login_time',
    dataIndex: 'last_login_time',
  },
  {
    title: '登录IP',
    key: 'ip',
    dataIndex: 'ip',
  },
  {
    title: '邮箱',
    key: 'mailbox',
    dataIndex: 'mailbox',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
