import { reactive } from 'vue'
import type { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { fireSourceTypeOptions, fireStatusOptions } from '@/views/system/fire-record/config'

export const conditionItems: FormItem[] = reactive([
  { key: 'key', label: '任务标识', type: 'input', value: '', placeholder: '请输入任务标识' },
  { key: 'name', label: '任务名称', type: 'input', value: '', placeholder: '请输入任务名称' },
  { key: 'description', label: '任务说明', type: 'input', value: '', placeholder: '请输入任务说明' },
  { key: 'cron', label: 'Cron', type: 'input', value: '', placeholder: '请输入 Cron 表达式' },
  { key: 'source_type', label: '触发类型', type: 'select', value: [], placeholder: '请选择触发类型', optionItems: fireSourceTypeOptions },
  { key: 'latest_status', label: '最近状态', type: 'select', value: [], placeholder: '请选择最近状态',
    optionItems: [...fireStatusOptions, { label: '尚未触发', value: 'untriggered' }] },
  { key: 'latest_error_message', label: '最近错误', type: 'input', value: '', placeholder: '请输入最近错误' },
])
enableMultiSelectSearch(conditionItems)
