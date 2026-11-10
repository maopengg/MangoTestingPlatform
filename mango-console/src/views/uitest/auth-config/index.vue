<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="UI授权管理" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="query.project_product"
        :reset-key="sidebarResetKey"
        @filter-change="onNavigationFilterChange"
        @search="onSearchRefresh"
        @reset-search="onReset"
      >
        <template #search>
          <ApiResourceSearchFilters
            :items="conditionItems"
            :field-names="fieldNames"
            :enum-store="enumStore"
            :user-list="userOptions"
            :users-loading="usersLoading"
            :option-overrides="{
              auth_type: enumStore.ui_auth_type,
              refresh_mode: enumStore.ui_auth_refresh_mode,
              last_refresh_status: enumStore.ui_auth_refresh_status,
            }"
            @search="onSearchRefresh"
            @reset="onReset"
          />
        </template>
        <div v-if="listError || usersError || enumsError || enumsLoading || operationError || taskError" class="mango-ui-auth-feedback">
          
          <a-alert v-if="operationError" type="error">{{ operationError }}</a-alert>
          <a-alert v-if="taskError" type="error">{{ taskError }}</a-alert>
        </div>
        <template #toolbar>
        <a-button  size="small" type="primary" @click="onAdd" data-testid="qa-views-uitest-auth-config-button-新增">新增</a-button>
        </template>
      <a-table
        class="mango-native-scroll-table"
        :bordered="false"
        :columns="columns"
        :data="rows"
        :loading="listLoading"
        :pagination="false"
        :scroll="{ x: tableScrollX, y: '100%' }"
        row-key="id"
      >
        <template #columns>
          <a-table-column v-for="item in columns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag
                v-if="record.test_env !== null && record.test_env !== undefined"
                :color="enumStore.colors[record.test_env]"
                size="small"
              >
                {{ enumStore.environment_type.find((item) => String(item.key) === String(record.test_env))?.title || `环境${record.test_env}` }}
              </a-tag>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'auth_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.auth_type]" size="small">
                {{ optionTitle(enumStore.ui_auth_type, record.auth_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'auth_config'" #cell="{ record }">
              <a-tooltip :content="getAuthConfigText(record)">
                <div class="mango-auth-table-summary">
                  {{ getAuthConfigText(record) }}
                </div>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'refresh_mode'" #cell="{ record }">
              <span v-if="record.auth_type === 3">-</span>
              <a-tag v-else :color="enumStore.colors[record.refresh_mode]" size="small">
                {{ optionTitle(enumStore.ui_auth_refresh_mode, record.refresh_mode) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'refresh_strategy'" #cell="{ record }">
              <a-tooltip :content="getRefreshStrategyText(record)">
                <div class="mango-auth-table-summary">
                  {{ getRefreshStrategyText(record) }}
                </div>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'token_ttl'" #cell="{ record }">
              {{ record.auth_type === 3 ? '-' : record.token_ttl ?? '-' }}
            </template>
            <template v-else-if="item.key === 'expires_at'" #cell="{ record }">
              {{ record.auth_type === 3 ? '-' : record.expires_at || '-' }}
            </template>
            <template v-else-if="item.key === 'last_refresh_status'" #cell="{ record }">
              <span v-if="record.auth_type === 3">-</span>
              <a-tooltip v-else :content="record.last_refresh_error || ''">
                <a-tag
                  :color="record.refreshing ? 'blue' : authRefreshStatusColor(record.last_refresh_status)"
                  size="small"
                >
                  {{
                    record.refreshing
                      ? '刷新中'
                      : optionTitle(enumStore.ui_auth_refresh_status, record.last_refresh_status)
                  }}
                </a-tag>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'last_refresh_time'" #cell="{ record }">
              {{ record.auth_type === 3 ? '-' : record.last_refresh_time || '-' }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :before-change="(checked) => onStatusChange(record, checked ? 1 : 0)"
                :model-value="record.status === 1"
                :loading="isOperationLoading(record.id, 'status')"
                :disabled="busy(record.id)"
              />
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="getAuthActions(record)"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <UiAuthEditorDialog ref="editorRef" @saved="refreshAfterEditor" />

  <UiAuthCacheDialog ref="cacheRef" />
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { Message, Modal } from '@arco-design/web-vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import UiAuthEditorDialog from './components/UiAuthEditorDialog.vue'
  import UiAuthCacheDialog from './components/UiAuthCacheDialog.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ApiResourceSearchFilters from '@/components/business/ApiResourceSearchFilters.vue'
  import { usePagination } from '@/hooks/table'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { formatProjectProductPath } from '@/utils/business-format'
  import { AUTH_REFRESH_STATUS_COLORS, getStatusTagColor } from '@/utils/status-color'
  import { createConditionItems, tableColumns, tableScrollX } from './config'
  import { uiAuthId, requiredUiAuthId, uiAuthResponse, readUiAuthOptions, type UiAuthId, type UiAuthOption } from './auth-editor-records'
  import { getAuthConfigText, getRefreshStrategyText, uiAuthListQuery, type UiAuthListRecord } from './auth-list-records'
  import { useAuthList } from './composables/useAuthList'
  import { useAuthTaskObserver } from './composables/useAuthTaskObserver'
  import { getFormItems } from '@/utils/datacleaning'
  import { getUserName } from '@/api/user/user'
  import {
    deleteUiAuthConfig,
    postUiAuthConfigClear,
    postUiAuthConfigRefresh,
    putUiAuthConfigStatus,
  } from '@/api/uitest/auth-config'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  type AuthTableAction = {
    label: string
    onClick: () => void
    danger?: boolean
    loading?: boolean
    disabled?: boolean
  }

  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const enumStore = useEnum()
  const conditionItems = createConditionItems()
  const authRefreshStatusColor = (value: number) =>
    getStatusTagColor(AUTH_REFRESH_STATUS_COLORS, value)
  let mounted = false, active = true, disposed = false, paused = false, contextVersion = 0, userVersion = 0, enumVersion = 0
  const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  function capture() { const key = identity(), version = contextVersion; return () => available() && key === identity() && version === contextVersion }
  const pagination = usePagination(doRefresh, () => list.loading)
  const list = useAuthList({ available, capture, query: normalizeQuery, pagination })
  const { rows, loading: listLoading, error: listError } = list
  const editorRef = ref<InstanceType<typeof UiAuthEditorDialog> | null>(null)
  const cacheRef = ref<InstanceType<typeof UiAuthCacheDialog> | null>(null)
  const userOptions = ref<UiAuthOption[]>([]), usersLoading = ref(false), usersError = ref('')
  const enumsLoading = ref(false), enumsError = ref(''), operationError = ref('')
  const sidebarResetKey = ref(0)
  const query = reactive<{ project_product: UiAuthId | null }>({ project_product: null })
  type AuthOperation = 'status' | 'refresh' | 'clear' | 'delete'
  const pendingRows = reactive(new Set<string>()), pendingOperations = reactive(new Set<string>())
  const confirmations = new Map<string, { close: () => void; valid: () => boolean }>()
  const rowKey = (id: UiAuthId) => JSON.stringify([identity(), String(id)])
  const manualBusy = (id: UiAuthId) => pendingRows.has(rowKey(id))
  const tasks = useAuthTaskObserver({ available, capture, owner: () => JSON.stringify([user.userId, user.roleId, user.selected_environment]), busy: manualBusy, onCaptured: () => { list.invalidate(); return doRefresh(false) } })
  const { error: taskError } = tasks
  const busy = (id: UiAuthId) => manualBusy(id) || tasks.isSubmitting(id)
  const isOperationLoading = (id: UiAuthId, action: AuthOperation) => pendingOperations.has(`${rowKey(id)}:${action}`)
  const columns = tableColumns
  function onSearchRefresh() {
    pagination.page = 1
    closeConfirmations()
    return doRefresh()
  }

  function onNavigationFilterChange({ projectProduct }: { projectProduct: unknown }) {
    query.project_product = uiAuthId(projectProduct)
    pagination.page = 1
    closeConfirmations()
    return doRefresh()
  }

  async function doRefresh(showLoading = true) { const loaded = await list.load(showLoading); if (loaded && available()) tasks.resume(rows.value); return loaded }
  function refreshAfterEditor() { list.invalidate(); return doRefresh() }

  function onReset() {
    query.project_product = null
    conditionItems.forEach(item => { if (item.reset) item.reset(); else item.value = item.multiple ? [] : '' })
    pagination.page = 1
    sidebarResetKey.value += 1
    closeConfirmations()
    return doRefresh()
  }

  function normalizeQuery() { return uiAuthListQuery(getFormItems(conditionItems), query.project_product, pagination.page, pagination.pageSize) }
  function optionTitle(options: unknown, value: UiAuthId) {
    try { return readUiAuthOptions(options ?? []).find(item => String(item.key) === String(value))?.title ?? '-' }
    catch { return '-' }
  }

  function onAdd() { return editorRef.value?.openCreate(navigationCreateRef.value?.getCreateDefaults().projectProduct ?? null) }
  function onEdit(record: UiAuthListRecord) { if (available() && !busy(record.id)) return editorRef.value?.openEdit(record) }
  function captureOperation() { const valid = capture(), key = JSON.stringify(normalizeQuery()); return () => valid() && key === JSON.stringify(normalizeQuery()) }

  async function runOperation(id: UiAuthId, action: AuthOperation, write: () => Promise<unknown>, message: string, current = captureOperation(), status?: 0 | 1): Promise<boolean> {
    if (!available() || !current() || busy(id)) return false
    const key = rowKey(id), actionKey = `${key}:${action}`, identityKey = identity()
    pendingRows.add(key); pendingOperations.add(actionKey); operationError.value = ''
    let committed = false
    try {
      uiAuthResponse(await write()); committed = true
      if (current()) {
        if (status !== undefined) list.updateStatus(id, status)
        Message.success(message)
      }
      return true
    } catch { if (current()) operationError.value = { status: '状态更新失败，请重试', refresh: '缓存刷新失败，请重试', clear: '缓存清空失败，请重试', delete: '删除失败，请重试' }[action]; return false }
    finally {
      pendingRows.delete(key); pendingOperations.delete(actionKey)
      if (committed && available() && identityKey === identity()) { list.invalidate(); void doRefresh(false) }
    }
  }
  function onStatusChange(record: UiAuthListRecord, status: 0 | 1) {
    const id = requiredUiAuthId(record.id)
    return runOperation(id, 'status', () => putUiAuthConfigStatus(id, status), '状态已更新', captureOperation(), status)
  }

  function onRefresh(record: UiAuthListRecord) {
    if ([1, 3].includes(record.auth_type)) return Promise.resolve(false)
    const id = requiredUiAuthId(record.id)
    return runOperation(id, 'refresh', () => postUiAuthConfigRefresh(id), '缓存已更新')
  }

  function onAutoStart(record: UiAuthListRecord) { return tasks.start(record, 'start') }
  function onAutoCapture(record: UiAuthListRecord) { return tasks.start(record, 'capture') }
  const isAuthTaskLoading = (id: UiAuthId, action: 'start' | 'capture') => tasks.isLoading(id, action)

  function getAuthActions(record: UiAuthListRecord): AuthTableAction[] {
    return [
      {  label: '缓存', onClick: () => onCache(record) },
      {
        label: '刷新',
        onClick: () => onRefresh(record),
        disabled: [1, 3].includes(record.auth_type) || busy(record.id),
        loading: isOperationLoading(record.id, 'refresh'),
      },
      {
        label: '自动授权',
        onClick: () => onAutoStart(record),
        disabled: record.auth_type !== 1 || busy(record.id),
        loading: isAuthTaskLoading(record.id, 'start'),
      },
      {
        label: '完成登录',
        onClick: () => onAutoCapture(record),
        disabled: record.auth_type !== 1 || busy(record.id),
        loading: isAuthTaskLoading(record.id, 'capture'),
      },
      {  label: '编辑', disabled: busy(record.id), onClick: () => onEdit(record) },
      {  label: '清空', danger: true, disabled: busy(record.id), loading: isOperationLoading(record.id, 'clear'), onClick: () => onClear(record) },
      {  label: '删除', danger: true, disabled: busy(record.id), loading: isOperationLoading(record.id, 'delete'), onClick: () => onDelete(record) },
    ]
  }

  function onClear(record: UiAuthListRecord) {
    const id = requiredUiAuthId(record.id)
    return runOperation(id, 'clear', () => postUiAuthConfigClear(id), '缓存已清空')
  }

  function onCache(record: unknown) { return cacheRef.value?.open(record) }

  function closeConfirmations() { for (const entry of confirmations.values()) entry.close(); confirmations.clear() }
  function onDelete(record: UiAuthListRecord) {
    const id = requiredUiAuthId(record.id), key = String(id), valid = capture(), queryKey = JSON.stringify(normalizeQuery())
    if (!available() || busy(id) || confirmations.has(key)) return
    let open = true
    const current = () => open && valid() && queryKey === JSON.stringify(normalizeQuery()) && confirmations.get(key)?.valid === current
    const close = () => { open = false; confirmations.delete(key); shell.close() }
    const shell = Modal.confirm({
      title: '删除授权',
      content: '是否要删除此 UI 授权配置？',
      okText: '删除', cancelText: '取消', okButtonProps: { status: 'danger' },
      onCancel: close,
      onBeforeOk: async () => {
        const success = await runOperation(id, 'delete', () => deleteUiAuthConfig(id), '删除成功', current)
        if (success && current()) close()
        return success
      },
    })
    confirmations.set(key, { close, valid: current })
  }

  async function loadUsers() {
    if (!available()) return
    const version = ++userVersion, current = capture(); usersLoading.value = true; usersError.value = ''
    try { const options = readUiAuthOptions(uiAuthResponse(await getUserName())); if (version === userVersion && current()) userOptions.value = options }
    catch (loadFailure0) { if (version === userVersion && current()) (reportLoadError(loadFailure0, "更新人加载失败，请重试", false), usersError.value = '更新人加载失败，请重试') }
    finally { if (version === userVersion) usersLoading.value = false }
  }
  async function loadEnums() {
    if (!available()) return
    const version = ++enumVersion, current = capture(); enumsLoading.value = true; enumsError.value = ''
    try { await enumStore.getEnum() }
    catch (loadFailure1) { if (version === enumVersion && current()) (reportLoadError(loadFailure1, "授权选项加载失败，请重试", false), enumsError.value = '授权选项加载失败，请重试') }
    finally { if (version === enumVersion) enumsLoading.value = false }
  }
  function invalidate(clear = false) {
    contextVersion++; userVersion++; enumVersion++; list.invalidate(clear); closeConfirmations()
    tasks.pause()
    editorRef.value?.close(); cacheRef.value?.close(); usersLoading.value = false; enumsLoading.value = false
    if (clear) { userOptions.value = []; usersError.value = ''; enumsError.value = ''; operationError.value = '' }
  }
  function resume() { if (!available()) return; paused = false; tasks.resume(rows.value); return Promise.allSettled([doRefresh(), loadUsers(), loadEnums()]) }
  function visibilityChanged() { if (available()) { if (paused) void resume() } else { paused = true; invalidate(true) } }
  watch(identity, () => { invalidate(true); pagination.page = 1; if (available()) void resume() }, { flush: 'sync' })
  onMounted(async () => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); await resume() })
  onActivated(() => { active = true; if (paused) void resume() })
  onDeactivated(() => { active = false; paused = true; invalidate(true) })
  onBeforeUnmount(() => { disposed = true; invalidate(true); document.removeEventListener('visibilitychange', visibilityChanged) })

</script>

<style scoped>
  .mango-ui-auth-feedback { display: grid; flex-shrink: 0; gap: var(--m-page-gap); }

  .mango-auth-table-summary {
    overflow: hidden;
    color: var(--m-text-2);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
