import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowReactive, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { putUiCaseStepsDetailed } from '@/api/uitest/case-steps-detailed'
import { uiCaseAssetId, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import { buildCaseNodeInputs, type CaseNodeInputContext } from '../case-node-inputs'

// 相同步骤在切换节点、卸载及重新打开期间仍共用实际请求锁；结束即移除。
const writes = shallowReactive(new Map<string, Promise<boolean>>())
export function useCaseNodeInputs(options: {
  enabled: () => boolean; caseId: () => unknown; caseStepId: () => unknown; pageStepId: () => unknown; nodeId: () => unknown; selection: () => unknown; data: () => unknown[]
  saved: (values: unknown[], context: CaseNodeInputContext) => void
}) {
  const user = useUserStore(), permission = usePermissionStore(), route = useRoute(), path = route.path, error = ref('')
  let active = true, disposed = false, version = 0
  const identity = () => JSON.stringify([route.fullPath, options.enabled(), options.caseId(), options.caseStepId(), options.pageStepId(), options.nodeId(), options.selection(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => !disposed && active && options.enabled() && route.path === path && document.visibilityState === 'visible'
  const key = () => JSON.stringify([options.caseId(), options.caseStepId()].map(value => String(uiCaseAssetId(value))))
  const saving = computed(() => writes.has(key()))
  function invalidate() { version++; error.value = '' }
  function save(input: unknown): Promise<boolean> {
    if (!available() || saving.value) return Promise.resolve(false)
    const caseId = uiCaseAssetId(options.caseId()), caseStepId = uiCaseAssetId(options.caseStepId()), pageStepId = uiCaseAssetId(options.pageStepId()), nodeId = uiCaseAssetId(options.nodeId())
    if (caseId === null || caseStepId === null || pageStepId === null || nodeId === null) { error.value = '未找到用例、步骤或节点信息'; return Promise.resolve(false) }
    const context: CaseNodeInputContext = { caseId, caseStepId, pageStepId }, identityKey = identity(), revision = version, writeKey = key()
    const current = () => available() && revision === version && identityKey === identity()
    let values: unknown[]
    try { values = buildCaseNodeInputs(options.data(), nodeId, input) } catch { error.value = 'Case 节点缓存无效，请返回用例编排执行“同步数据”后重试'; return Promise.resolve(false) }
    error.value = ''
    const request = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const response = await putUiCaseStepsDetailed({ id: caseStepId, case_data: values }, caseId)
        uiCaseAssetResponse(response)
        if (!current()) return false
        options.saved(values, context); Message.success('保存成功'); return true
      } catch { if (current()) error.value = '节点参数保存失败，草稿已保留，请重试'; return false }
      finally { if (writes.get(writeKey) === request) writes.delete(writeKey) }
    })
    writes.set(writeKey, request); return request
  }
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate() }
  watch(identity, invalidate, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onActivated(() => { active = true })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { saving, error, save }
}
