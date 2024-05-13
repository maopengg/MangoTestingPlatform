import { FormItem } from '@/types/components'
import { reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
export const columns = reactive([
  {
    title: '序号',
    dataIndex: 'id',
  },
  {
    title: '创建时间',
    dataIndex: 'create_time',
  },
  {
    title: '更新时间',
    dataIndex: 'update_time',
  },
  {
    title: '模块名称',
    dataIndex: 'name',
  },
  {
    title: '上级模块(一级模块)',
    dataIndex: 'superior_module',
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 130,
  },
])

export const formItems: FormItem[] = reactive([
  {
    label: '模块名称',
    key: 'name',
    value: '',
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
    label: '上级模块',
    key: 'superior_module',
    value: '',
    placeholder: '请输入上级模块',
    required: false,
    type: 'input',
    validator: function () {
      // if (!this.value) {
      //   Message.error(this.placeholder || '')
      // return false
      // }
      return true
    },
  },
])
