
import { reportLoadError } from '@/utils/load-error'
import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { getUiPublic } from '@/api/uitest/public'
import { getUiAuthConfig } from '@/api/uitest/auth-config'
import { getDataFactoryDatasourceAlias } from '@/api/data-factory'
import { requiredUiCaseAssetId, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import { readUiCaseAuthChoices, readUiCaseDatasourceChoices, readUiCasePublicChoices } from '../configuration-options'

export function useCaseConfigurationOptions(productId: () => unknown) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  let active = true, disposed = false, version = 0
  const identity = () => JSON.stringify([route.path, route.fullPath, productId(), user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  function capture() { const key = identity(), sequence = version; return () => available() && key === identity() && sequence === version }
  function resource<T>(read: (id: UiCaseAssetId) => Promise<unknown>, parse: (value: unknown) => T[], failure: string) {
    const rows = shallowRef<T[]>([]), loading = ref(false), error = ref('')
    let sequence = 0, reading: { current: () => boolean; promise: Promise<boolean> } | null = null
    function invalidate(clear: boolean) { sequence++; reading = null; loading.value = false; error.value = ''; if (clear) rows.value = [] }
    function load(showLoading = true): Promise<boolean> {
      if (!available()) return Promise.resolve(false)
      let id: UiCaseAssetId
      try { id = requiredUiCaseAssetId(productId()) } catch { return Promise.resolve(false) }
      if (reading?.current()) { if (showLoading) loading.value = true; return reading.promise }
      const valid = capture(), currentSequence = ++sequence, current = () => valid() && currentSequence === sequence
      loading.value = showLoading; error.value = ''
      const promise = Promise.resolve().then(async () => {
        try { if (!current()) return false; const value = parse(await read(id)); if (!current()) return false; rows.value = value; return true }
        catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), error.value = failure); return false }
        finally { if (currentSequence === sequence) { loading.value = false; reading = null } }
      })
      reading = { current, promise }; return promise
    }
    return { rows, loading, error, load, invalidate }
  }
  const publicVariables = resource(id => getUiPublic({ page: 1, pageSize: 10000, project_product_id: id }), readUiCasePublicChoices, '全局变量加载失败，请重试')
  const authorizations = resource(id => getUiAuthConfig({ page: 1, pageSize: 10000, project_product_id: id }), readUiCaseAuthChoices, '授权配置加载失败，请重试')
  const datasources = resource(id => getDataFactoryDatasourceAlias({ project_product: id, status: 1 }), readUiCaseDatasourceChoices, '逻辑数据源加载失败，请重试')
  const resources = [publicVariables, authorizations, datasources]
  function invalidate(clear = false) { version++; resources.forEach(item => item.invalidate(clear)) }
  function loadAll(showLoading = true) { return Promise.all(resources.map(item => item.load(showLoading))) }
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate(); else if (available()) void loadAll(false) }
  watch(identity, () => { invalidate(true); if (available()) void loadAll() }, { flush: 'sync' })
  onMounted(() => { document.addEventListener('visibilitychange', visibilityChanged); void loadAll() })
  onActivated(() => { active = true; if (available()) void loadAll(false) })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(true); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { publicVariables, authorizations, datasources }
}
