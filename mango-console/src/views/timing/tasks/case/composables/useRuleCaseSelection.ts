
import { reportLoadError } from '@/utils/load-error'
import { reactive, ref } from 'vue'
import { usePagination } from '@/hooks/table'
import { getSystemTaskSelectionCases } from '@/api/system/tasks'
import { parseRuleCases, taskCaseLeaf, type RuleCaseRecord } from '../case-records'
import type { TaskCaseId } from '../task-config'

interface RuleSelectionContext {
  getTaskId: () => TaskCaseId | ''
  isManual: () => boolean
  available: () => boolean
  captureContext: () => () => boolean
}

export function useRuleCaseSelection(context: RuleSelectionContext) {
  const ruleCases = ref<RuleCaseRecord[]>([]), ruleLoading = ref(false), ruleError = ref(''), ruleSelectedCount = ref(0)
  const ruleFilter = reactive({ caseId: '', caseName: '', caseTypes: [] as number[], moduleId: '' as TaskCaseId, scenarioTags: [] as string[] })
  const rulePagination = usePagination(loadRuleCases, ruleLoading)
  let requestId = 0

  async function loadRuleCases(resetPage = false): Promise<void> {
    if (!context.available()) { ruleLoading.value = false; return }
    const request = ++requestId, taskId = context.getTaskId(), active = context.captureContext()
    const current = () => active() && request === requestId
    if (taskId === '' || context.isManual()) { ruleLoading.value = false; return }
    if (resetPage === true) rulePagination.page = 1
    ruleLoading.value = true; ruleError.value = ''
    try {
      const moduleId = taskCaseLeaf(ruleFilter.moduleId)
      const response = await getSystemTaskSelectionCases({
        task_id: taskId,
        case_id: ruleFilter.caseId.trim() || undefined,
        case_name: ruleFilter.caseName.trim() || undefined,
        case_types: ruleFilter.caseTypes.length ? ruleFilter.caseTypes.join(',') : undefined,
        module_id: moduleId === '' ? undefined : moduleId,
        scenario_tags: ruleFilter.scenarioTags.length ? ruleFilter.scenarioTags.join(',') : undefined,
        page: rulePagination.page, pageSize: rulePagination.pageSize,
      })
      if (!current()) return
      const result = parseRuleCases(response)
      rulePagination.setTotalSize(result.total)
      const lastPage = Math.max(1, Math.ceil(result.total / rulePagination.pageSize))
      if (rulePagination.page > lastPage) { rulePagination.page = lastPage; await loadRuleCases(); return }
      ruleCases.value = result.rows; ruleSelectedCount.value = result.selectedCount
    } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "规则匹配用例加载失败，请重试", false), ruleError.value = '规则匹配用例加载失败，请重试') }
    finally { if (current()) ruleLoading.value = false }
  }

  function invalidate() { requestId++; ruleLoading.value = false }
  function reset() {
    invalidate(); ruleCases.value = []; ruleSelectedCount.value = 0; ruleError.value = ''
    Object.assign(ruleFilter, { caseId: '', caseName: '', caseTypes: [], moduleId: '', scenarioTags: [] })
    rulePagination.page = 1; rulePagination.setTotalSize(0)
  }
  return { ruleCases, ruleLoading, ruleError, ruleSelectedCount, ruleFilter, rulePagination, loadRuleCases, invalidate, reset }
}
