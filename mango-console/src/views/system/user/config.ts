import { FormItem } from '@/types/components'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
import { updateTimeColumn, updateUserColumn } from '@/utils/update-user'

const table = useTable()
export const tableScrollX = 1810

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入用户ID',
    value: createIdSearchValue(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '昵称',
    type: 'input',
    placeholder: '请输入昵称',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'username',
    label: '账号',
    type: 'input',
    placeholder: '请输入账号',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
])
export const formItems: FormItem[] = reactive([
  {
    label: '昵称',
    key: 'name',
    value: ref(''),
    placeholder: '请输入用户昵称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '登录邮箱',
    key: 'username',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入登录邮箱',
    validator: function () {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(this.value || ''))) {
        Message.error('请输入正确的登录邮箱')
        return false
      }
      return true
    },
  },
  {
    label: '登录邮箱',
    key: 'email',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入登录邮箱',
    validator: function () {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(this.value || ''))) {
        Message.error('请输入正确的邮箱地址')
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
    value: ref(''),
    type: 'select',
    required: false,
    placeholder: '请选择用户角色，留空为游客',
    validator: function () {
      if (this.value === null && this.value === '') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '超级管理员',
    key: 'is_super_admin',
    value: ref(false),
    type: 'switch',
    required: false,
    placeholder: '',
  },
  {
    label: '所属部门',
    key: 'department_ids',
    value: ref([]),
    type: 'department-select',
    required: false,
    placeholder: '请选择用户所属部门',
  },
])
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '昵称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',

    width: 200,
  },
  {
    title: '登录邮箱',
    key: 'username',
    dataIndex: 'username',
    align: 'left',
    width: 200,
  },
  {
    title: '角色',
    key: 'role',
    dataIndex: 'role',
    align: 'left',
    width: 200,
  },
  {
    title: '超管',
    key: 'is_super_admin',
    dataIndex: 'is_super_admin',
    align: 'center',
    width: 90,
  },
  {
    title: '部门',
    key: 'departments',
    dataIndex: 'departments',
    align: 'left',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },

  {
    title: '登录IP',
    key: 'ip',
    dataIndex: 'ip',
    align: 'left',
    width: 170,
  },
  {
    title: '最近登录时间',
    key: 'last_login_time',
    dataIndex: 'last_login_time',
    width: 180,
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
