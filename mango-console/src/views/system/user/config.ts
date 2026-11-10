import { FormItem } from '@/types/components'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { updateTimeColumn, updateUserColumn } from '@/utils/update-user'

export const tableScrollX = 1810

export const createConditionItems = (): FormItem[] => reactive([
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
export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '昵称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',

    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '登录邮箱',
    key: 'username',
    dataIndex: 'username',
    ellipsis: true,
    tooltip: true,
    align: 'left',
    width: 200,
  },
  {
    title: '角色',
    key: 'role',
    dataIndex: 'role',
    ellipsis: true,
    tooltip: true,
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
    ellipsis: true,
    tooltip: true,
    align: 'left',
    width: 170,
  },
  {
    title: '最近登录时间',
    key: 'last_login_time',
    dataIndex: 'last_login_time',
    width: 180,
  },
  { ...updateUserColumn(), key: 'update_user' },
  { ...updateTimeColumn(), key: 'update_time' },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
