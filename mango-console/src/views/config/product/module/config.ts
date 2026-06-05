import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'

export const columns = reactive([
  {
    title: '序号',
    dataIndex: 'id',
    width: 80,
  },
  {
    title: '三级模块（模块名称）',
    dataIndex: 'name',
    align: 'left',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '一级模块',
    dataIndex: 'superior_module_1',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '二级模块',
    dataIndex: 'superior_module_2',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '创建时间',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '更新时间',
    dataIndex: 'update_time',
    width: 180,
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 170,
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '三级模块',
    key: 'name',
    value: ref(''),
    placeholder: '请输入模块名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '上级模块(二级模块)',
    key: 'superior_module_2',
    value: ref(''),
    placeholder: '请输入上级模块',
    required: false,
    type: 'input',
    validator: function () {
      return true
    },
  },
  {
    label: '上级模块(一级模块)',
    key: 'superior_module_1',
    value: ref(''),
    placeholder: '请输入上级模块',
    required: false,
    type: 'input',
    validator: function () {
      return true
    },
  },
])
