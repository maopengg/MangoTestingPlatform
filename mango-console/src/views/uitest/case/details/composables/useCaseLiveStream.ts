
import { reportLoadError } from '@/utils/load-error'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { getSystemSocketCurrentActuatorStatus } from '@/api/system/socket_api'
import { waitForMinimumLoading } from '@/utils/minimum-loading'
import type { UiCaseAssetId } from '@/components/business/ui-case-step-create'
import { readCaseLiveActuators, type CaseLiveActuator } from '../live-actuators'
import type { CaseExecutionLaunch } from '../case-execution'

export function useCaseLiveStream(options: {
  caseId: () => UiCaseAssetId | null; busy: () => boolean; executionActive: () => boolean
  shown: (current: () => boolean) => Promise<unknown>
}) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const visible = ref(false), opening = ref(false), rows = shallowRef<CaseLiveActuator[]>([]), loading = ref(false), error = ref(''), selected = ref(''), executionId = ref(''), actuator = ref('')
  let active = true, disposed = false, version = 0, viewVersion = 0, sequence = 0, readyNotified = false, resumeVisible = false
  let reading: { current: () => boolean; promise: Promise<boolean> } | null = null, openingRequest: Promise<boolean> | null = null
  const identity = () => JSON.stringify([route.path, route.fullPath, options.caseId(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible' && options.caseId() !== null
  function capture() { const key = identity(), revision = version; return () => available() && key === identity() && revision === version }
  const disabled = (row: CaseLiveActuator) => row.full && !row.users.includes(user.userName)
  const choices = computed(() => rows.value.map(row => ({ ...row, disabled: disabled(row) })))
  function invalidate(clear = false) {
    version++; viewVersion++; sequence++; reading = null; loading.value = false
    openingRequest = null; opening.value = false
    if (clear) { visible.value = false; resumeVisible = false; rows.value = []; selected.value = ''; executionId.value = ''; actuator.value = ''; error.value = ''; readyNotified = false; openingRequest = null; opening.value = false }
  }
  function load(showMessage = false, showLoading = true): Promise<boolean> {
    if (!available()) return Promise.resolve(false)
    if (reading?.current()) { if (showLoading) loading.value = true; return reading.promise }
    const valid = capture(), request = ++sequence, current = () => valid() && request === sequence
    loading.value = showLoading; error.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const next = readCaseLiveActuators(await getSystemSocketCurrentActuatorStatus())
        if (!current()) return false
        rows.value = next
        if (!next.some(row => row.username === selected.value && !disabled(row))) selected.value = (next.find(row => row.owner && !disabled(row)) ?? next.find(row => !disabled(row)))?.username ?? ''
        if (showMessage && visible.value) { if (next.length) Message.success('执行器列表已刷新'); else Message.warning('暂无支持 Web 直播的在线执行器') }
        return true
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "执行器列表加载失败，请重试", false), error.value = '执行器列表加载失败，请重试'); return false }
      finally { if (request === sequence) { loading.value = false; reading = null } }
    })
    reading = { current, promise }; return promise
  }
  function close() {
    viewVersion++; visible.value = false; resumeVisible = false
    openingRequest = null; opening.value = false
    if (!options.executionActive()) { executionId.value = ''; actuator.value = ''; readyNotified = false }
  }
  function open(): Promise<boolean> {
    if (openingRequest) return openingRequest
    if (!available()) return Promise.resolve(false)
    const valid = capture(), revision = ++viewVersion, current = () => valid() && revision === viewVersion && visible.value
    const startedAt = Date.now(); visible.value = true; opening.value = true; readyNotified = false
    const promise = Promise.resolve().then(async () => {
      try { if (!await load() || !current()) return false; await options.shown(current); return current() }
      catch (loadFailure1) { if (current()) (reportLoadError(loadFailure1, "直播区域加载失败，请重新打开", false), error.value = '直播区域加载失败，请重新打开'); return false }
      finally { await waitForMinimumLoading(startedAt); if (openingRequest === promise) { opening.value = false; openingRequest = null } }
    })
    openingRequest = promise; return promise
  }
  function choose(username: string) { if (!options.busy() && !options.executionActive() && (!username || rows.value.some(row => row.username === username && !disabled(row)))) selected.value = username }
  async function prepare(withLive: boolean, current: () => boolean): Promise<CaseExecutionLaunch | null> {
    if (!current() || !available()) return null
    const valid = capture()
    if (!withLive) return { withLive: false }
    if ((!selected.value || error.value) && !await load()) return null
    if (!valid() || !current()) return null
    const choice = rows.value.find(row => row.username === selected.value && !disabled(row))
    if (!choice) { error.value = '请选择支持 Web 直播的在线执行器'; return null }
    return { withLive: true, actuatorUsername: choice.username }
  }
  function started(launch: CaseExecutionLaunch & { executionId: string }) {
    if (!available()) return
    executionId.value = launch.withLive ? launch.executionId : ''; actuator.value = launch.withLive ? launch.actuatorUsername ?? '' : ''; readyNotified = false
  }
  function ready() { if (!available() || !visible.value || !executionId.value || readyNotified) return; readyNotified = true; Message.success('实时画面连接成功，正在展示执行过程') }
  function finish(completedExecutionId: string) {
    if (!available() || !completedExecutionId || completedExecutionId !== executionId.value) return
    const wasVisible = visible.value
    // 执行器已经保留收尾画面；前端不重复等待五秒。
    close(); if (wasVisible) Message.success('Case 执行完成，实时画面已自动收起')
  }
  function pause() { resumeVisible = resumeVisible || visible.value; visible.value = false; invalidate() }
  function resume() { if (available() && resumeVisible) { visible.value = true; resumeVisible = false; void load(false, false) } }
  function visibilityChanged() { if (document.visibilityState !== 'visible') pause(); else resume() }
  watch(identity, () => invalidate(true), { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; invalidate(true); document.removeEventListener('visibilitychange', visibilityChanged) })
  return {
    visible: computed({ get: () => visible.value, set: value => { if (value) void open(); else close() } }),
    selected: computed({ get: () => selected.value, set: choose }), choices, loading, error, opening,
    executionId: computed(() => executionId.value), actuator: computed(() => actuator.value),
    load, open, close, toggle: () => visible.value ? close() : open(), prepare, started, ready, finish,
  }
}
