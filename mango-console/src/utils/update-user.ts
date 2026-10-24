import { h, ref } from 'vue'
import type { TableColumnData } from '@arco-design/web-vue'
import type { FormItem } from '@/types/components'

export function createUpdateUserCondition(): FormItem {
  return {
    key: 'update_user',
    label: '更新人',
    type: 'select',
    placeholder: '请选择更新人',
    value: ref([]),
    multiple: true,
    searchOperator: 'in',
    optionItems: [],
    reset: function () {
      this.value = []
    },
  }
}

export function updateUserColumn(width = 110): TableColumnData {
  return {
    title: '更新人',
    key: 'update_user',
    dataIndex: 'update_user',
    width,
    render: ({ record }) => {
      const updateUser = record?.update_user_info || record?.update_user
      return h('span', updateUser?.name || updateUser?.username || '-')
    },
  }
}

export function updateTimeColumn(): TableColumnData {
  return {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
  }
}

export function setUpdateUserOptions(conditionItems: FormItem[], options: any[]) {
  const item = conditionItems.find((it) => it.key === 'update_user')
  if (item) {
    item.optionItems = options
  }
}
