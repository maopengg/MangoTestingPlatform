import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'

const table = useTable()

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入ID',
    value: createIdSearchValue(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '授权名称',
    type: 'input',
    placeholder: '请输入授权名称',
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
    reset: function () {},
  },
  {
    key: 'test_env',
    label: '被测环境',
    value: ref(''),
    type: 'select',
    placeholder: '请选择被测环境',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'auth_type',
    label: '授权方式',
    value: ref(''),
    type: 'select',
    placeholder: '请选择授权方式',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'refresh_mode',
    label: '刷新方式',
    value: ref(''),
    type: 'select',
    placeholder: '请选择刷新方式',
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'last_refresh_status',
    label: '刷新状态',
    value: ref(''),
    type: 'select',
    placeholder: '请选择刷新状态',
    reset: function () {
      this.value = ''
    },
  },
  createUpdateUserCondition(),
])
enableMultiSelectSearch(conditionItems)

export const authFormSections = [
  { key: 'basic', title: '基础信息', description: '设置授权名称、所属产品及被测环境',
    itemKeys: ['name', 'project_product', 'test_env'] },
  { key: 'authentication', title: '认证配置', description: '设置认证方式、适用目标及认证变量',
    itemKeys: ['auth_type', 'api_info', 'target_address', 'public_variable_ids', 'custom_code'] },
  { key: 'refresh', title: '刷新策略', description: '设置有效期、刷新方式与到期通知',
    itemKeys: ['refresh_mode', 'token_ttl', 'refresh_margin', 'time_task', 'expire_notice_minutes', 'notice_group'] },
]

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
    label: '被测环境',
    key: 'test_env',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择被测环境',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '授权名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入授权名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '适用目标地址', key: 'target_address', value: ref(''), type: 'select', required: false,
    placeholder: '不选择则使用默认地址',
  },
  {
    label: '授权方式',
    key: 'auth_type',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择授权方式',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '登录接口',
    key: 'api_info',
    value: ref(''),
    type: 'select',
    required: false,
    placeholder: '请选择登录接口',
  },
  {
    label: '关联公共变量',
    key: 'public_variable_ids',
    value: ref([]),
    type: 'select',
    multiple: true,
    placeholder: '选填，选择认证所需的租户、用户等变量',
  },
  {
    label: '自定义代码',
    key: 'custom_code',
    value: ref(''),
    type: 'code',
    required: false,
    placeholder: '请选择自定义代码后自动生成示例，可按需修改返回的 dict',
  },
  {
    label: '有效期(分钟)',
    key: 'token_ttl',
    value: ref(1440),
    type: 'number',
    min: 1,
    required: true,
    placeholder: '请输入Token有效期',
    validator: function () {
      if (!this.value || Number(this.value) <= 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '提前刷新(分钟)',
    key: 'refresh_margin',
    value: ref(10),
    type: 'number',
    min: 10,
    required: true,
    placeholder: '请输入提前刷新时间',
    validator: function () {
      if (this.value === '' || Number(this.value) < 10) {
        Message.error('提前刷新时间不能少于10分钟')
        return false
      }
      return true
    },
  },
  {
    label: '提前通知(分钟)',
    key: 'expire_notice_minutes',
    value: ref(30),
    type: 'number',
    min: 10,
    required: true,
    placeholder: '请输入提前通知时间',
    validator: function () {
      if (this.value === '' || Number(this.value) < 10) {
        Message.error('提前通知时间不能少于10分钟')
        return false
      }
      return true
    },
  },
  {
    label: '刷新方式',
    key: 'refresh_mode',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择刷新方式',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '定时策略',
    key: 'time_task',
    value: ref(''),
    type: 'select',
    required: false,
    placeholder: '请选择定时策略',
  },
  {
    label: '通知组',
    key: 'notice_group',
    value: ref(''),
    type: 'select',
    required: false,
    placeholder: '请选择通知组',
  },
])

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '授权名称',
    key: 'name',
    dataIndex: 'name',
    width: 240,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '被测环境',
    key: 'test_env',
    dataIndex: 'test_env',
    width: 90,
  },
  {
    title: '授权方式',
    key: 'auth_type',
    dataIndex: 'auth_type',
    width: 110,
  },
  {
    title: '适用目标地址', key: 'target_address', dataIndex: 'target_address',
    width: 240, align: 'left', ellipsis: true, tooltip: true,
  },
  {
    title: '授权来源',
    key: 'auth_source',
    dataIndex: 'auth_source',
    align: 'left',
    width: 220,
  },
  {
    title: '刷新方式',
    key: 'refresh_mode',
    dataIndex: 'refresh_mode',
    width: 160,
  },
  {
    title: '刷新策略',
    key: 'time_task',
    dataIndex: 'time_task',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 160,
  },
  {
    title: '过期时间',
    key: 'expires_at',
    dataIndex: 'expires_at',
    width: 180,
  },
  {
    title: '刷新状态',
    key: 'last_refresh_status',
    dataIndex: 'last_refresh_status',
    width: 110,
  },
  {
    title: '默认开启',
    key: 'status',
    dataIndex: 'status',
    width: 90,
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

export const tableScrollX = tableColumns.reduce(
  (total: number, column: { width?: number }) => total + (column.width || 0),
  40,
)
