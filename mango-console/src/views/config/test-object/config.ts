import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateTimeColumn, updateUserColumn } from '@/utils/update-user'

export function createConditionItems() {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入测试对象ID',
      value: createIdSearchValue(),
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
    {
      key: 'project_product',
      label: '项目/产品',
      type: 'cascader',
      placeholder: '请选择项目/产品',
      value: ref(''),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'environment',
      label: '部署环境',
      value: ref(''),
      type: 'select',
      placeholder: '请选择部署环境',
      optionItems: [],
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'auto_type',
      label: '自动化类型',
      value: ref(''),
      type: 'select',
      placeholder: '请选择自动化类型',
      optionItems: [],
      reset: function () {
        this.value = ''
      },
    },
    createUpdateUserCondition(),
  ]
  return enableMultiSelectSearch(reactive(fields))
}
export const tableScrollX = 1560

export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '环境名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '域名/包名/路径',
    key: 'value',
    dataIndex: 'value',
    align: 'left',
    width: 400,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '部署环境',
    key: 'environment',
    dataIndex: 'environment',
    align: 'center',
    width: 100,
  },
  {
    title: '自动化类型',
    key: 'auto_type',
    dataIndex: 'auto_type',
    align: 'center',
    width: 130,
  },
  { ...updateUserColumn(), key: 'update_user' },
  { ...updateTimeColumn(), key: 'update_time' },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    fixed: 'right',
    width: 160,
  },
])
