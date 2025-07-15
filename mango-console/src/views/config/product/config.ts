import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

interface Project {
  id: number
  // 添加 Project 模型中其他需要的字段
}

interface ProjectProduct {
  id: number
  create_time: Date
  update_time: Date
  project: Project | null
  name: string
  auto_type: number
  client_type: number
}

export const formItems: FormItem[] = reactive([
  {
    label: '项目名称',
    key: 'project',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: 'UI端类型',
    key: 'ui_client_type',
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
    label: 'API端类型',
    key: 'api_client_type',
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
    label: '产品名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入产品名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
])
export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入产品ID',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '产品名称',
    type: 'input',
    placeholder: '请输入产品名称',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
])
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 170,
  },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 170,
  },
  {
    title: '项目名称',
    key: 'project',
    dataIndex: 'project',
    align: 'left',

    width: 200,
  },
  {
    title: '产品名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
  },
  {
    title: 'UI产品类型',
    key: 'ui_client_type',
    dataIndex: 'ui_client_type',
    width: 120,
  },
  {
    title: 'API产品类型',
    key: 'api_client_type',
    dataIndex: 'api_client_type',
    width: 120,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
