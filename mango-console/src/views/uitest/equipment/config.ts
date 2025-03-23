import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { useTable, useTableColumn } from '@/hooks/table'
import { Message } from '@arco-design/web-vue'

const table = useTable()

export const formItems: FormItem[] = reactive([
  {
    label: '驱动类型',
    key: 'type',
    value: ref(''),
    type: 'select',
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
    key: 'web_type',
    value: ref(''),
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
    label: '并行数',
    key: 'web_parallel',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择浏览器并行数',
    validator: function () {
      return true
    },
  },
  {
    label: '设备模式',
    key: 'web_h5',
    value: ref(''),
    type: 'select',
    required: false,
    placeholder: '请选择设备模式（H5）（不必填可以不用填）',
    validator: function () {
      return true
    },
  },
  {
    label: '浏览器路径',
    key: 'web_path',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入浏览器路径（不必填可以不用填）',
    validator: function () {
      return true
    },
  },
  {
    label: '最大化',
    key: 'web_max',
    value: ref(''),
    placeholder: '请输入浏览器调试端口（不必填可以不用填）',
    required: false,
    type: 'switch',
    validator: function () {
      return true
    },
  },

  {
    label: '视频录制',
    key: 'web_recording',
    value: ref(''),
    type: 'switch',
    required: false,
    placeholder: '请输入浏览器路径（不必填可以不用填）',
    validator: function () {
      return true
    },
  },

  {
    label: '无头模式',
    key: 'web_headers',
    value: ref(''),
    type: 'switch',
    required: false,
    placeholder: '请输入无头模式（不必填可以不用填）',
    validator: function () {
      return true
    },
  },
])
export const androidFormItems: FormItem[] = reactive([
  {
    label: '安卓设备号',
    key: 'and_equipment',
    value: ref(''),
    placeholder: '请输入安卓设备号或IP+端口',
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
])
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '驱动类型',
    key: 'type',
    dataIndex: 'type',
  },
  {
    title: '所属用户',
    key: 'user_id',
    dataIndex: 'user_id',
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
  },
  {
    title: '浏览器类型',
    key: 'web_type',
    dataIndex: 'web_type',
  },
  {
    title: '最大化',
    key: 'web_max',
    dataIndex: 'web_max',
  },
  {
    title: '录制',
    key: 'web_recording',
    dataIndex: 'web_recording',
  },
  {
    title: '并行数',
    key: 'web_parallel',
    dataIndex: 'web_parallel',
  },
  {
    title: '设备模式（H5）',
    key: 'web_h5',
    dataIndex: 'web_h5',
  },
  {
    title: '浏览器路径',
    key: 'web_path',
    dataIndex: 'web_path',
  },
  {
    title: '无头模式',
    key: 'web_headers',
    dataIndex: 'web_headers',
  },
  {
    title: '安卓设备号',
    key: 'and_equipment',
    dataIndex: 'and_equipment',
    align: 'left',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150,
  },
])
