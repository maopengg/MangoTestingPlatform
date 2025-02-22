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
    placeholder: '请输入测试对象ID',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '环境名称',
    type: 'input',
    placeholder: '请输入环境名称',
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
    label: '环境名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入环境名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '测试对象',
    key: 'value',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入域名/包名/路径',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },

  {
    label: '部署环境',
    key: 'environment',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择绑定环境',
    validator: function () {
      if (this.value === null && this.value === '') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '自动化类型',
    key: 'auto_type',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择产品的端类型',
    validator: function () {
      if (this.value === null && this.value === '') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '负责人名称',
    key: 'executor_name',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请输入负责人名称',
    validator: function () {
      if (this.value === null && this.value === '') {
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
    title: '环境名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
  },
  {
    title: '域名/包名/路径',
    key: 'value',
    dataIndex: 'value',
    align: 'left',
  },
  {
    title: '部署环境',
    key: 'environment',
    dataIndex: 'environment',
    width: 150,
  },
  {
    title: '自动化类型',
    key: 'auto_type',
    dataIndex: 'auto_type',
  },
  {
    title: '负责人',
    key: 'executor_name',
    dataIndex: 'executor_name',
  },
  {
    title: '查询权限',
    key: 'db_c_status',
    dataIndex: 'db_c_status',
  },
  {
    title: '增删改权限',
    key: 'db_rud_status',
    dataIndex: 'db_rud_status',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
