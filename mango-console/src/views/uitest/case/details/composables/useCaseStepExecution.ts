import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { getUiStepsTest } from '@/api/uitest/page-steps'
import { uiCaseAssetId, uiCaseAssetObject, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import type { CaseStepRow } from '../step-list'

interface StepExecutionSnapshot { caseId: UiCaseAssetId; recordId: UiCaseAssetId; pageStepId: UiCaseAssetId; environment: UiCaseAssetId }
export function useCaseStepExecution(options: {
  caseId: () => UiCaseAssetId | null; rows: () => readonly CaseStepRow[]; busy: () => boolean
  refresh: (current: () => boolean) => Promise<unknown>
}) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), path = route.path
  const pending = shallowRef<StepExecutionSnapshot | null>(null), error = ref('')
  let active = true, disposed = false, revision = 0, writing: Promise<boolean> | null = null
  let failed: { snapshot: StepExecutionSnapshot; current: () => boolean; submitted: boolean } | null = null
  const identity = () => JSON.stringify([route.path, route.fullPath, options.caseId(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === path && document.visibilityState === 'visible'
  function capture() { const key = identity(), version = revision; return () => available() && key === identity() && version === revision }
  function invalidate() { revision++; error.value = ''; failed = null }
  function exists(snapshot: StepExecutionSnapshot) { return String(options.caseId()) === String(snapshot.caseId) && options.rows().some(row => String(row.id) === String(snapshot.recordId) && String(row.page_step?.id) === String(snapshot.pageStepId)) }
  function submit(snapshot: StepExecutionSnapshot, submitted = false): Promise<boolean> {
    if (writing || options.busy() || !available() || !exists(snapshot)) return Promise.resolve(false)
    const valid = capture(), current = () => valid() && exists(snapshot)
    const saved = { ...snapshot }; pending.value = saved; error.value = ''; failed = null
    const request = Promise.resolve().then(async () => {
      let accepted = submitted
      try {
        if (!current()) return false
        if (!accepted) {
          const response = uiCaseAssetObject(await getUiStepsTest(saved.pageStepId, saved.environment))
          if (response.code !== 200) throw Error('Step submission failed')
          accepted = true
          if (!current()) return false
          Message.loading(typeof response.msg === 'string' ? response.msg : '单步执行已提交')
        }
        await options.refresh(current)
        return current()
      } catch {
        if (current()) {
          error.value = accepted ? '单步执行已提交，结果刷新失败，请重试刷新' : '单步执行提交失败，请重试；连接中断时请先确认执行器是否已收到任务'
          failed = { snapshot: saved, current, submitted: accepted }
        }
        return false
      } finally { if (writing === request) { writing = null; pending.value = null } }
    })
    writing = request; return request
  }
  function run(recordId: UiCaseAssetId): Promise<boolean> {
    if (writing || options.busy() || !available()) return Promise.resolve(false)
    const caseId = uiCaseAssetId(options.caseId()), environment = uiCaseAssetId(user.selected_environment)
    if (caseId === null) return Promise.resolve(false)
    if (environment === null) { Message.error('请先选择用例执行的环境'); return Promise.resolve(false) }
    const row = options.rows().find(row => String(row.id) === String(recordId))
    if (!row?.page_step) return Promise.resolve(false)
    return submit({ caseId, recordId: row.id, pageStepId: row.page_step.id, environment })
  }
  function retry(): Promise<boolean> { const previous = failed; return previous?.current() ? submit(previous.snapshot, previous.submitted) : Promise.resolve(false) }
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate() }
  watch(identity, invalidate, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onActivated(() => { active = true })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { pending: computed(() => pending.value), running: computed(() => pending.value !== null), error, run, retry }
}
