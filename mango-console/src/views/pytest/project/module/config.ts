import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
export const columns: any = reactive([
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
    title: '文件夹名称',
    dataIndex: 'file_name',
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
])
