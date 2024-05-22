import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { useTable, useTableColumn } from '@/hooks/table'
import { Message } from '@arco-design/web-vue'
const table = useTable()
export const formItems: FormItem[] = reactive([
  {
    label: '驱动类型',
    key: 'type',
    value: '',
    type: 'radio',
    required: true,
    placeholder: '请选择驱动类型',
    validator: function () {
      return true
    },
  },
])
export const webFormItems: FormItem[] = reactive([
  {
    label: '浏览器类型',
    key: 'browser_type',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请选择浏览器类型',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '设备模式',
    key: 'device',
    value: '',
    type: 'select',
    required: false,
    placeholder: '请选择设备',
    validator: function () {
      return true
    },
  },
  {
    label: '浏览器端口',
    key: 'browser_port',
    value: '',
    placeholder: '请输入浏览器调试端口',
    required: false,
    type: 'input',
    validator: function () {
      return true
    },
  },
  {
    label: '浏览器路径',
    key: 'browser_path',
    value: '',
    type: 'textarea',
    required: false,
    placeholder: '请输入浏览器路径',
    validator: function () {
      return true
    },
  },
  {
    label: '无头模式',
    key: 'is_headless',
    value: '',
    type: 'switch',
    required: false,
    placeholder: '请输入无头模式',
    validator: function () {
      return true
    },
  },
])
export const androidFormItems: FormItem[] = reactive([
  {
    label: '安卓设备号',
    key: 'equipment',
    value: '',
    placeholder: '请输入安卓设备号或IP+端口',
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
])
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '驱动类型',
    key: 'type',
    dataIndex: 'type',
  },
  {
    title: '浏览器类型',
    key: 'browser_type',
    dataIndex: 'browser_type',
  },
  {
    title: '设备模式',
    key: 'device',
    dataIndex: 'device',
  },
  {
    title: '浏览器端口',
    key: 'browser_port',
    dataIndex: 'browser_port',
  },
  {
    title: '浏览器地址',
    key: 'browser_path',
    dataIndex: 'browser_path',
    align: 'left',
  },
  {
    title: '安卓设备号',
    key: 'equipment',
    dataIndex: 'equipment',
    align: 'left',
  },
  {
    title: '所属用户',
    key: 'user_id',
    dataIndex: 'user_id',
  },
  {
    title: '是否开启无头',
    key: 'is_headless',
    dataIndex: 'is_headless',
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
