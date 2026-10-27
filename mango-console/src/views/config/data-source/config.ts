import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'

export const bindingColumns = [
  {
    title: '逻辑数据库',
    dataIndex: 'datasource_alias__name',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '项目/产品',
    dataIndex: 'project_product_path',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  { title: '被测环境', slotName: 'environment', width: 100, align: 'center' as const },
  { title: '实际数据库 / Schema', slotName: 'target', width: 220, ellipsis: true, tooltip: true },
  { title: '读取', slotName: 'read', width: 80, align: 'center' as const },
  { title: '写入', slotName: 'write', width: 80, align: 'center' as const },
  {
    title: '操作',
    slotName: 'actions',
    width: 160,
    fixed: 'right' as const,
    align: 'center' as const,
  },
]
export const databaseColumns = [
  { title: '数据库名称', dataIndex: 'name', ellipsis: true, tooltip: true },
  { title: '操作', slotName: 'query', width: 160, fixed: 'right' as const, align: 'center' as const },
]
export const formItems: FormItem[] = reactive([
  {
    label: '数据库分类',
    key: 'source_category',
    value: ref(0),
    type: 'select',
    required: true,
    placeholder: '请选择数据库分类',
  },
  {
    label: '数据库类型',
    key: 'db_type',
    value: ref(0),
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
    label: '数据库别名',
    key: 'display_name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入数据库别名，例如：订单测试库',
    validator: function () {
      if (!String(this.value || '').trim()) {
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
    placeholder: '请输入数据库域名或IP',
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
    label: '数据库文件',
    key: 'file_path',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入服务端已存在的 SQLite 文件路径',
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
    required: false,
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
    required: false,
    placeholder: '无密码可留空；编辑留空则不修改',
  },
])
