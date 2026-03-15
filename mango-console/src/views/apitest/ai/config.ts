import { reactive } from 'vue'
import { useTableColumn } from '@/hooks/table'

/** 用例列表表格列定义 */
export const caseListColumns = useTableColumn([
  { title: '序号', dataIndex: 'index', width: 60 },
  { title: '用例名称', dataIndex: 'case_name', width: 240 },
  { title: '步骤名称', dataIndex: 'step_name' },
  { title: '操作', key: 'actions', width: 80 },
])

/** importForm 的初始值工厂，每次 resetAll 时调用 */
export function makeImportForm() {
  return reactive({
    project_product: '' as any,
    module_id: '' as any,
    name: '',
    text: '',
  })
}

/** casePreview 的初始值工厂 */
export function makeCasePreview() {
  return reactive({
    api_info_id: null as any,
    case_people_id: null as any,
    cases: [] as { case_name: string; step_name: string }[],
  })
}

/** 步骤条配置 */
export const steps = [
  { title: '粘贴接口信息' },
  { title: '确认接口 & 测试' },
  { title: '确认用例配置' },
]
