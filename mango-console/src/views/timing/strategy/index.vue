<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader :show-filter="true" title="定时策略" @search="onSearch" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="conditionItems" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <a-input v-if="item.type === 'input'" v-model="item.value" :placeholder="item.placeholder" @blur="onSearch" />
              <a-select v-else-if="item.type === 'select'" v-model="item.value" :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined" :field-names="fieldNames" :options="updaterOptions"
                :loading="updaterLoading" :placeholder="item.placeholder" allow-clear allow-search @change="onSearch" />
            </a-form-item>
          </a-form>

        </template>
      </TableHeader>
    </template>
    <template #default>
      <TableTabs>
        <template #extra>
          <a-space><span>注意：新增的定时策略需要联系管理员重启服务才会生效！</span>
            <a-button size="small" type="primary" :disabled="writeBusy" @click="onAdd" data-testid="qa-views-timing-strategy-button-新增">新增</a-button>
          </a-space>
        </template>
      </TableTabs>

      <a-table :scroll="{ x: tableScrollX }" :bordered="false" :data="rows" :loading="listLoading" :pagination="false" :row-key="rowKey">
        <template #columns>
          <a-table-column v-for="item of tableColumns" :key="item.key" :align="item.align" :data-index="item.key" :fixed="item.fixed"
            :title="item.title" :width="item.width" :ellipsis="item.ellipsis" :tooltip="item.tooltip">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">{{ record.update_user?.name || record.update_user?.username || '-' }}</template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions :actions="[
                { label: '编辑', disabled: writeBusy, onClick: () => onUpdate(record) },
                { label: '删除', danger: true, disabled: writeBusy, loading: deletingId !== null && String(deletingId) === String(record.id), onClick: () => onDelete(record) },
              ]" />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>
  <ModalDialog modal-class="mango-simple-form-modal" ref="modalDialogRef" :title="actionTitle" :width="560" @confirm="onDataForm" @cancel="closeEditor">
    <template #content>
      <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal">
        <a-form-item class="mango-form-item__require mango-simple-form-item" label="定时器介绍"><a-input v-model="form.name" placeholder="请输入定时器的介绍" /></a-form-item>
        <a-form-item class="mango-form-item__require mango-simple-form-item" label="cron"><a-input v-model="form.cron" placeholder="请输入正确的cron表达式" /></a-form-item>
        <a-alert v-if="saveError" type="error">{{ saveError }}</a-alert>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination, useRowKey } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import type { ModalDialogType } from '@/types/components'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { deleteSystemTime, getSystemTime, postSystemTime, putSystemTime } from '@/api/system/time'
  import { getUserName } from '@/api/user/user'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import TableTabs from '@/components/table/TableTabs.vue'
  import { tableColumns, createConditionItems, tableScrollX } from './config'
  import { copyStrategyRecord, createStrategyDraft, parseStrategies, parseStrategyUsers, strategyPayload, strategyQuery, strategySuccess, validateStrategyDraft } from './strategy-records'
  import type { StrategyId, StrategyRecord, StrategyUserOption } from './strategy-records'

  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const conditionItems = createConditionItems(), rows = ref<StrategyRecord[]>([]), listLoading = ref(true), listError = ref('')
  const updaterOptions = ref<StrategyUserOption[]>([]), updaterLoading = ref(false), updaterError = ref('')
  const pagination = usePagination(doRefresh, listLoading), rowKey = useRowKey('id')
  const modalDialogRef = ref<ModalDialogType | null>(null), form = reactive(createStrategyDraft())
  const editorId = ref<StrategyId | null>(null), editorVisible = ref(false), saving = ref(false), saveError = ref('')
  const deletingId = ref<StrategyId | null>(null), writeBusy = computed(() => saving.value || deletingId.value !== null)
  const actionTitle = computed(() => editorId.value === null ? '新增' : '编辑')
  const listRequests = useLatestRequest(), updaterRequests = useLatestRequest()
  let active = true, mounted = false, disposed = false, contextVersion = 0, editorVersion = 0, confirmationVersion = 0
  let needsList = true, needsUpdaters = true
  let pendingList: { key: string; promise: Promise<void> } | null = null, pendingUpdaters: Promise<void> | null = null
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  function guard() {
    const version = contextVersion, key = identity()
    return () => available() && version === contextVersion && key === identity()
  }
  function buildQuery() { return strategyQuery(getFormItems(conditionItems)) }
  function doRefresh(): Promise<void> {
    if (!available()) { needsList = true; listLoading.value = false; return Promise.resolve() }
    let query: Record<string, unknown>
    try { query = { ...buildQuery(), page: pagination.page, pageSize: pagination.pageSize } }
    catch (loadFailure0) { listRequests.invalidateRequests(); pendingList = null; listLoading.value = false; (reportLoadError(loadFailure0, "加载失败，请重试", false), listError.value = '搜索条件格式异常，请检查后重试'); return Promise.resolve() }
    const signature = JSON.stringify([identity(), query])
    if (pendingList?.key === signature) return pendingList.promise
    const request = listRequests.beginRequest(), current = guard(), valid = () => current() && listRequests.isLatestRequest(request)
    needsList = false; listLoading.value = true; listError.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        const response = await getSystemTime(query)
        if (!valid()) return
        const result = parseStrategies(response)
        pagination.setTotalSize(result.total)
        const lastPage = Math.max(1, Math.ceil(result.total / pagination.pageSize))
        if (pagination.page > lastPage) { pagination.page = lastPage; await doRefresh(); return }
        rows.value = result.rows
      } catch (loadFailure1) { if (valid()) { (reportLoadError(loadFailure1, "定时策略加载失败，请重试", false), listError.value = '定时策略加载失败，请重试'); needsList = true } }
      finally { if (valid()) { listLoading.value = false; pendingList = null } }
    })
    pendingList = { key: signature, promise }; return promise
  }
  function onSearch() { pagination.page = 1; return doRefresh() }
  function resetConditions() { for (const item of conditionItems) { if (item.reset) item.reset(); else item.value = item.multiple ? [] : '' } }
  function onResetSearch() { resetConditions(); return onSearch() }
  function loadUpdaters(): Promise<void> {
    if (!available()) { needsUpdaters = true; return Promise.resolve() }
    if (pendingUpdaters) return pendingUpdaters
    const request = updaterRequests.beginRequest(), current = guard(), valid = () => current() && updaterRequests.isLatestRequest(request)
    needsUpdaters = false; updaterLoading.value = true; updaterError.value = ''
    const promise = Promise.resolve().then(async () => {
      try { if (valid()) { const response = await getUserName(); if (valid()) updaterOptions.value = parseStrategyUsers(response) } }
      catch (loadFailure2) { if (valid()) { (reportLoadError(loadFailure2, "更新人选项加载失败，请重试", false), updaterError.value = '更新人选项加载失败，请重试'); needsUpdaters = true } }
      finally { if (valid()) { updaterLoading.value = false; pendingUpdaters = null } }
    })
    pendingUpdaters = promise; return promise
  }
  function closeEditor() {
    editorVersion++; editorVisible.value = false; editorId.value = null; saveError.value = ''
    Object.assign(form, createStrategyDraft()); void modalDialogRef.value?.close()
  }
  function closeConfirmation() { confirmationVersion++; confirmation?.close(); confirmation = null }
  function onAdd() {
    if (!available() || writeBusy.value) return
    closeConfirmation(); closeEditor(); editorVisible.value = true; void modalDialogRef.value?.show()
  }
  function onUpdate(row: StrategyRecord) {
    if (!available() || writeBusy.value) return
    const record = copyStrategyRecord(row)
    closeConfirmation(); closeEditor(); editorId.value = record.id
    Object.assign(form, createStrategyDraft(record)); editorVisible.value = true; void modalDialogRef.value?.show()
  }
  async function onDataForm(): Promise<void> {
    if (saving.value) return
    if (!available() || !editorVisible.value || deletingId.value !== null) { modalDialogRef.value?.setConfirmLoading(false); return }
    const error = validateStrategyDraft(form)
    if (error) { Message.error(error); modalDialogRef.value?.setConfirmLoading(false); return }
    const current = guard(), version = editorVersion, id = editorId.value, key = identity()
    const valid = () => current() && version === editorVersion && editorVisible.value
    let refreshAttempted = false
    try {
      const payload = strategyPayload(form, id)
      saving.value = true; saveError.value = ''; modalDialogRef.value?.setConfirmLoading(true)
      const response = id === null ? await postSystemTime(payload) : await putSystemTime(payload)
      const message = strategySuccess(response, '保存成功')
      if (key === identity()) needsList = true
      if (!valid()) return
      closeEditor(); Message.success(message); refreshAttempted = true; await doRefresh()
    } catch { if (valid()) saveError.value = '保存失败，请检查输入并重试' }
    finally {
      saving.value = false
      if (valid()) modalDialogRef.value?.setConfirmLoading(false)
      if (!refreshAttempted || !current()) resume()
    }
  }
  function onDelete(row: StrategyRecord) {
    if (!available() || writeBusy.value) return
    const record = copyStrategyRecord(row), current = guard(), key = identity()
    closeEditor(); closeConfirmation()
    const version = confirmationVersion, valid = () => current() && version === confirmationVersion
    confirmation = Modal.confirm({ title: '提示', content: '是否要删除此定时策略？', cancelText: '取消', okText: '删除', okButtonProps: { status: 'danger' },
      onCancel: () => { if (version === confirmationVersion) closeConfirmation() },
      onBeforeOk: async () => {
        if (!valid() || writeBusy.value) return false
        deletingId.value = record.id
        let refreshAttempted = false
        try {
          const response = await deleteSystemTime(record.id), message = strategySuccess(response, '删除成功')
          if (key === identity()) needsList = true
          if (!valid()) return false
          closeConfirmation(); Message.success(message); refreshAttempted = true; await doRefresh(); return true
        } catch { if (valid()) Message.error('删除失败，请重试'); return false }
        finally { deletingId.value = null; if (!refreshAttempted || !current()) resume() }
      },
    })
  }
  function pause() {
    contextVersion++; listRequests.invalidateRequests(); updaterRequests.invalidateRequests()
    pendingList = null; pendingUpdaters = null; needsList = true; needsUpdaters = true
    listLoading.value = false; updaterLoading.value = false; closeEditor(); closeConfirmation()
  }
  function resume() {
    if (!available() || writeBusy.value) return
    if (needsList) void doRefresh()
    if (needsUpdaters) void loadUpdaters()
  }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(identity, () => {
    pause(); rows.value = []; updaterOptions.value = []; resetConditions()
    pagination.page = 1; pagination.setTotalSize(0); listError.value = ''; updaterError.value = ''
    resume()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-strategy-error { color: var(--m-danger); margin-top: var(--m-page-gap); }
</style>
