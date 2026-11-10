
import { reportLoadError } from '@/utils/load-error'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { deleteDataFactoryCaseConfig, getDataFactoryCaseConfig, postDataFactoryCaseConfig, putDataFactoryCaseConfig, putDataFactoryCaseConfigSort } from '@/api/data-factory'
import { factoryConfigId, factoryConfigObject, factoryConfigResponse, factoryConfigWrite, readFactoryConfigRows, type FactoryConfigId, type FactoryConfigRecord, type FactoryConfigSummary, type FactoryConfigWrite } from '../case-config-record'

interface Mutation { kind: 'save' | 'status' | 'sort' | 'delete'; recordId: FactoryConfigId | null }
export interface FactoryConfigMutationResult { accepted: boolean; current: () => boolean }
export function useCaseConfigCollection(options: {
  caseId: () => FactoryConfigId | null | undefined; sourceType: () => number | undefined
  local: () => boolean; readonly: () => boolean; configs: () => unknown[]
  changed: (summary: FactoryConfigSummary) => void; invalidated: () => void
}) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), path = route.path
  const rows = shallowRef<FactoryConfigRecord[]>([]), loading = ref(false), loaded = ref(false), loadError = ref(''), operationError = ref(''), pending = shallowRef<Mutation | null>(null)
  let active = true, disposed = false, version = 0, sequence = 0, writing: Promise<FactoryConfigMutationResult> | null = null
  let reading: { current: () => boolean; promise: Promise<boolean> } | null = null
  const failed = shallowRef<{ current: () => boolean; retry: () => Promise<FactoryConfigMutationResult> } | null>(null)
  const identity = () => JSON.stringify([route.path, route.fullPath, options.caseId(), options.sourceType(), options.local(), options.readonly(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === path && document.visibilityState === 'visible'
  function capture() { const key = identity(), revision = version; return () => available() && key === identity() && revision === version }
  const summary = computed<FactoryConfigSummary>(() => ({ count: loaded.value ? rows.value.length : null, loading: loading.value, error: loadError.value }))
  watch(summary, value => options.changed(value), { immediate: true })
  function invalidate(clear = false) { version++; sequence++; reading = null; loading.value = false; loadError.value = ''; operationError.value = ''; failed.value = null; if (clear) { rows.value = []; loaded.value = false }; options.invalidated() }
  function load(showLoading = true): Promise<boolean> {
    if (!available()) return Promise.resolve(false)
    if (reading?.current()) { if (showLoading) loading.value = true; return reading.promise }
    const sourceId = factoryConfigId(options.caseId()), sourceType = options.sourceType(), local = options.local(), readonly = options.readonly()
    const valid = capture(), request = ++sequence, current = () => valid() && request === sequence
    loadError.value = ''; loading.value = showLoading
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        let next: FactoryConfigRecord[]
        if (local || readonly) next = readFactoryConfigRows(options.configs())
        else if (sourceId === null || sourceType == null) next = []
        else next = readFactoryConfigRows(factoryConfigResponse(await getDataFactoryCaseConfig({ source_type: sourceType, source_id: sourceId })), { sourceId, sourceType })
        if (!current()) return false
        rows.value = next; loaded.value = true; return true
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "数据工厂配置加载失败，请重试", false), loadError.value = '数据工厂配置加载失败，请重试'); return false }
      finally { if (request === sequence) { reading = null; loading.value = false } }
    })
    reading = { current, promise }; return promise
  }
  const rejected = (): FactoryConfigMutationResult => ({ accepted: false, current: () => false })
  function mutate(operation: Mutation, action: () => Promise<unknown>, scope = capture(), acknowledged: () => void = () => {}): Promise<FactoryConfigMutationResult> {
    if (writing || !scope() || options.local() || options.readonly()) return Promise.resolve(rejected())
    // 写入前启动的列表响应不能在成功后覆盖新列表。
    sequence++; reading = null; loading.value = false; operationError.value = ''; failed.value = null; pending.value = operation
    const request = Promise.resolve().then(async () => {
      let accepted = false
      try {
        if (!scope()) return rejected()
        const response = await action()
        factoryConfigResponse(response); accepted = true
        if (!scope()) return { accepted, current: scope }
        acknowledged()
        const message = factoryConfigObject(response).msg
        Message.success(typeof message === 'string' ? message : '操作成功')
        sequence++; reading = null; loading.value = false
        await load(false)
        return { accepted, current: scope }
      } catch {
        if (scope()) {
          operationError.value = accepted ? '操作已完成，请重试刷新列表' : '数据工厂配置操作失败，请重试'
          if (!accepted && operation.kind !== 'save') failed.value = { current: scope, retry: () => mutate(operation, action, scope, acknowledged) }
        }
        return { accepted, current: scope }
      } finally { if (writing === request) { writing = null; pending.value = null } }
    })
    writing = request; return request
  }
  function owner() { const sourceId = factoryConfigId(options.caseId()), sourceType = options.sourceType(); return sourceId === null || sourceType == null ? null : { source_id: sourceId, source_type: sourceType } }
  function save(value: FactoryConfigWrite): Promise<FactoryConfigMutationResult> {
    const target = owner(); if (!target || writing) return Promise.resolve(rejected())
    let snapshot: FactoryConfigWrite
    try { snapshot = factoryConfigWrite(value) } catch { operationError.value = '数据工厂配置格式无效，请检查后重试'; return Promise.resolve(rejected()) }
    const payload = { ...snapshot, ...target }
    return mutate({ kind: 'save', recordId: snapshot.id }, () => snapshot.id === null ? postDataFactoryCaseConfig(payload) : putDataFactoryCaseConfig(payload), capture(), () => { loaded.value = false })
  }
  function status(recordId: FactoryConfigId, enabled: boolean): Promise<boolean> {
    const row = rows.value.find(row => String(row.id) === String(recordId)), target = owner()
    if (!row?.template || !target) return Promise.resolve(false)
    const payload = { ...factoryConfigWrite({ ...row, template: row.template.id, status: enabled ? 1 : 0 }), ...target }
    return mutate({ kind: 'status', recordId: row.id }, () => putDataFactoryCaseConfig(payload), capture(), () => { rows.value = rows.value.map(item => String(item.id) === String(payload.id) ? { ...item, status: payload.status } : item) }).then(result => result.accepted && result.current())
  }
  function sort(order: FactoryConfigId[]): Promise<FactoryConfigMutationResult> {
    if (order.length !== rows.value.length || new Set(order.map(String)).size !== order.length || !order.every(id => rows.value.some(row => String(row.id) === String(id)))) return Promise.resolve(rejected())
    const sourceType = options.sourceType(); if (sourceType == null) return Promise.resolve(rejected())
    const payload = { source_type: sourceType, case_sort_list: order.map((id, sort) => ({ id, sort })) }
    return mutate({ kind: 'sort', recordId: null }, () => putDataFactoryCaseConfigSort(payload), capture(), () => {
      const byId = new Map(rows.value.map(row => [String(row.id), row])), saved = new Set(payload.case_sort_list.map(row => String(row.id)))
      rows.value = [...payload.case_sort_list.flatMap(item => { const row = byId.get(String(item.id)); return row ? [{ ...row, sort: item.sort }] : [] }), ...rows.value.filter(row => !saved.has(String(row.id)))]
    })
  }
  function remove(recordId: FactoryConfigId, current = capture()): Promise<FactoryConfigMutationResult> {
    const row = rows.value.find(row => String(row.id) === String(recordId))
    if (!row) return Promise.resolve(rejected())
    const id = row.id
    return mutate({ kind: 'delete', recordId: id }, () => deleteDataFactoryCaseConfig(id), current, () => { rows.value = rows.value.filter(row => String(row.id) !== String(id)) })
  }
  function retry() { const previous = failed.value; return previous?.current() ? previous.retry() : Promise.resolve(rejected()) }
  function resume() { if (available()) void load(false) }
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate(); else resume() }
  watch(identity, () => { invalidate(true); if (available()) void load() }, { flush: 'sync' })
  watch(options.configs, () => { if (options.local() || options.readonly()) { invalidate(true); if (available()) void load() } }, { deep: true })
  onMounted(() => { document.addEventListener('visibilitychange', visibilityChanged); void load() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(true); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { rows: computed(() => rows.value), loading, loadError, operationError, pending: computed(() => pending.value), summary, capture, load, save, status, sort, remove, retry, canRetry: computed(() => !!failed.value?.current()) }
}
