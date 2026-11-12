<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader :show-filter="true" title="用户管理" @search="onSearch" @reset-search="onResetSearch">
        <template #search-content>
          <a-form layout="inline" :model="conditionItems" @keyup.enter="onSearch">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <a-input v-model="item.value" :placeholder="item.placeholder" @blur="onSearch" />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <TableTabs>
        <template #extra>
          <a-button type="primary" size="small" :disabled="writeBusy" @click="onRegisterUser" data-testid="qa-views-system-user-button-注册用户">注册用户</a-button>
        </template>
      </TableTabs>
      <MangoRequestFeedback v-if="routeRefreshError" :message="(routeRefreshError)"><a-link :loading="routeRefreshing" @click="refreshOwnRoutes">刷新菜单</a-link></MangoRequestFeedback>
      <a-table :scroll="{ x: tableScrollX }" :bordered="false" :loading="listLoading" :data="rows" :pagination="false" :row-key="rowKey"
        :row-selection="{ selectedRowKeys, showCheckedAll }" @selection-change="onSelectionChange">
        <template #columns>
          <a-table-column v-for="item of tableColumns" :key="item.key" :align="item.align" :title="item.title" :width="item.width" :data-index="item.key" :fixed="item.fixed" :ellipsis="item.ellipsis" :tooltip="item.tooltip">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'role'" #cell="{ record }">{{ record.role?.name || '游客' }}</template>
            <template v-else-if="item.key === 'is_super_admin'" #cell="{ record }">
              <a-switch :model-value="record.is_super_admin" :checked-value="true" :unchecked-value="false" :loading="isRowBusy(record.id, 'super')" :disabled="writeBusy" :before-change="(checked) => onSuperAdminChange(record, checked)"  />
            </template>
            <template v-else-if="item.key === 'departments'" #cell="{ record }">{{ departmentNames(record) }}</template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">{{ record.update_user?.name || record.update_user?.username || '-' }}</template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions :actions="[
                { label: '编辑', disabled: writeBusy, onClick: () => onUpdate(record) },
                { label: '重置密码', disabled: writeBusy, loading: isRowBusy(record.id, 'password'), onClick: () => onResetPassword(record) },
                { label: '重置 MCP Key', danger: true, disabled: writeBusy, loading: isRowBusy(record.id, 'key'), onClick: () => onResetApiKey(record) },
                { label: '删除', danger: true, disabled: writeBusy, loading: isRowBusy(record.id, 'delete'), onClick: () => onDelete(record) },
              ]" />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>
  <UserEditorDialog ref="editor" :context-key="identityKey" :locked="rowOperation !== null || routeRefreshing" @busy="onEditorBusy" @committed="onEditorCommitted" @saved="onUserSaved" @email-settings="goToEmailConfig" />
  <ModalDialog modal-class="mango-simple-form-modal" ref="resetPasswordDialogRef" title="重置密码" :width="560" @confirm="onResetPasswordConfirm" @cancel="closePassword">
    <template #content>
      <a-form auto-label-width class="mango-simple-form" :model="passwordModel" layout="horizontal">
        <a-form-item class="mango-simple-form-item" label="用户账号"><a-input :model-value="passwordTarget?.username ?? ''" disabled /></a-form-item>
        <a-form-item class="mango-simple-form-item" label="发送方式">
          <span>系统生成随机密码并发送到该用户的登录邮箱。</span>
          <template #extra>历史账号需先由用户在个人中心修改密码并切换为邮箱登录；发送前请确认已完成 <a-link @click="goToEmailConfig">邮箱配置</a-link>。</template>
        </a-form-item>
        <MangoRequestFeedback v-if="passwordError" :message="(passwordError)" />
      </a-form>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination, useRowKey, useRowSelection } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { getFormItems } from '@/utils/datacleaning'
  import type { ModalDialogType } from '@/types/components'
  import { deleteUserInfo, getUserInfo, putUserInfo, resetUserApiKey, resetUserPassword } from '@/api/user/user'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import TableTabs from '@/components/table/TableTabs.vue'
  import UserEditorDialog from './components/UserEditorDialog.vue'
  import { createConditionItems, tableColumns, tableScrollX } from './config'
  import { copyUserRecord, createUserDraft, parseUserList, userSearchQuery, userSuccess, userUpdatePayload } from './user-records'
  import type { UserEditorHandle, UserId, UserRecord } from './user-records'

  const user = useUserStore(), permission = usePermissionStore(), route = useRoute(), router = useRouter(), pagePath = route.path
  const conditionItems = createConditionItems(), rows = ref<UserRecord[]>([]), listLoading = ref(true), listError = ref('')
  const pagination = usePagination(doRefresh, listLoading), rowKey = useRowKey('id')
  const { selectedRowKeys, showCheckedAll, onSelectionChange } = useRowSelection()
  const editor = ref<UserEditorHandle | null>(null), editorSaving = ref(false)
  const resetPasswordDialogRef = ref<ModalDialogType | null>(null), passwordTarget = ref<UserRecord | null>(null), passwordError = ref('')
  const passwordModel = computed(() => ({ username: passwordTarget.value?.username ?? '' }))
  const rowOperation = ref<{ id: UserId; action: 'super' | 'password' | 'key' | 'delete' } | null>(null)
  const routeRefreshing = ref(false), routeRefreshError = ref('')
  const writeBusy = computed(() => editorSaving.value || rowOperation.value !== null || routeRefreshing.value)
  const identityKey = computed(() => JSON.stringify([sessionKey(), permission.permissionKeys]))
  const listRequests = useLatestRequest()
  let active = true, mounted = false, disposed = false, contextVersion = 0, passwordVersion = 0, confirmationVersion = 0, routeVersion = 0
  let needsList = true, pendingOwnSession: string | null = null
  let pendingList: { key: string; promise: Promise<void> } | null = null
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  function sessionKey() { return JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment]) }
  function guard() {
    const version = contextVersion, key = identityKey.value
    return () => available() && version === contextVersion && key === identityKey.value
  }
  function isRowBusy(id: UserId, action: NonNullable<typeof rowOperation.value>['action']) { return rowOperation.value?.action === action && String(rowOperation.value.id) === String(id) }
  function departmentNames(record: UserRecord) { return record.departments.map(item => item.name).join('、') || '-' }

  function doRefresh(): Promise<void> {
    if (!available()) { needsList = true; listLoading.value = false; return Promise.resolve() }
    let query: Record<string, unknown>
    try { query = { ...userSearchQuery(getFormItems(conditionItems)), page: pagination.page, pageSize: pagination.pageSize } }
    catch (loadFailure0) { listRequests.invalidateRequests(); pendingList = null; listLoading.value = false; (reportLoadError(loadFailure0, "加载失败，请重试", false), listError.value = '搜索条件格式异常，请检查后重试'); return Promise.resolve() }
    const signature = JSON.stringify([identityKey.value, query])
    if (pendingList?.key === signature) return pendingList.promise
    const request = listRequests.beginRequest(), current = guard(), valid = () => current() && listRequests.isLatestRequest(request)
    needsList = false; listLoading.value = true; listError.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!valid()) return
        const response = await getUserInfo(query)
        if (!valid()) return
        const result = parseUserList(response)
        pagination.setTotalSize(result.total)
        const lastPage = Math.max(1, Math.ceil(result.total / pagination.pageSize))
        if (pagination.page > lastPage) { pagination.page = lastPage; await doRefresh(); return }
        rows.value = result.rows; selectedRowKeys.value = []
      } catch (loadFailure1) { if (valid()) { (reportLoadError(loadFailure1, "用户列表加载失败，请重试", false), listError.value = '用户列表加载失败，请重试'); needsList = true } }
      finally { if (valid()) { listLoading.value = false; pendingList = null } }
    })
    pendingList = { key: signature, promise }; return promise
  }
  function onSearch() { pagination.page = 1; return doRefresh() }
  function resetConditions() { for (const item of conditionItems) { if (item.reset) item.reset(); else item.value = '' } }
  function onResetSearch() { resetConditions(); return onSearch() }
  function onRegisterUser() { if (available() && !writeBusy.value) { closePassword(); editor.value?.openRegister() } }
  function onUpdate(record: UserRecord) { if (available() && !writeBusy.value) { closePassword(); editor.value?.openEdit(record) } }
  function closePassword() { passwordVersion++; passwordTarget.value = null; passwordError.value = ''; void resetPasswordDialogRef.value?.close() }
  function onResetPassword(record: UserRecord) {
    if (!available() || writeBusy.value) return
    editor.value?.close(); closePassword()
    if (record.requires_email_login_migration) {
      closeConfirmation()
      confirmation = Modal.warning({ title: '请先切换为邮箱登录', content: '该用户仍使用历史账号登录。请通知用户先在“个人中心”修改密码并绑定登录邮箱，完成后再重置密码。', okText: '知道了' })
      return
    }
    passwordTarget.value = copyUserRecord(record); void resetPasswordDialogRef.value?.show()
  }
  async function onResetPasswordConfirm(): Promise<void> {
    if (writeBusy.value) return
    if (!available() || !passwordTarget.value) { resetPasswordDialogRef.value?.setConfirmLoading(false); return }
    const id = passwordTarget.value.id, version = passwordVersion, current = guard()
    const valid = () => current() && version === passwordVersion && passwordTarget.value !== null
    rowOperation.value = { id, action: 'password' }; passwordError.value = ''; resetPasswordDialogRef.value?.setConfirmLoading(true)
    try {
      const response = await resetUserPassword({ id })
      if (!valid()) return
      const message = userSuccess(response, '密码已重置'); closePassword(); Message.success(message); await doRefresh()
    } catch (requestFailure) { if (valid()) passwordError.value = requestFailureMessage(requestFailure, '重置密码失败，请重试') }
    finally { rowOperation.value = null; if (valid()) resetPasswordDialogRef.value?.setConfirmLoading(false); resume() }
  }
  function closeConfirmation() { confirmationVersion++; confirmation?.close(); confirmation = null }
  function confirmOperation(record: UserRecord, action: 'key' | 'delete') {
    if (!available() || writeBusy.value) return
    const row = copyUserRecord(record), current = guard(), session = sessionKey()
    editor.value?.close(); closePassword(); closeConfirmation()
    const version = confirmationVersion, valid = () => current() && version === confirmationVersion
    const handle = Modal.confirm({
      title: action === 'delete' ? '提示' : '重置 MCP Key',
      content: action === 'delete' ? '是否要删除此用户？' : `重置后，${row.name || row.username || `用户 ${row.id}`} 当前使用的 MCP Key 将立即失效，是否继续？`,
      cancelText: '取消', okText: action === 'delete' ? '删除' : '确认重置', okButtonProps: { status: 'danger' },
      onCancel: () => { if (version === confirmationVersion) closeConfirmation() },
      onBeforeOk: async () => {
        if (!valid() || writeBusy.value) return false
        rowOperation.value = { id: row.id, action }
        try {
          const response = action === 'delete' ? await deleteUserInfo(row.id) : await resetUserApiKey({ id: row.id })
          const message = userSuccess(response, action === 'delete' ? '删除成功' : 'MCP Key 已重置')
          if (session === sessionKey() && action === 'delete') {
            needsList = true
            if (String(row.id) === String(user.userId)) pendingOwnSession = session
          }
          if (!valid()) return false
          // 先关闭确认框，列表刷新失败不改变已成功的写操作结果。
          closeConfirmation(); Message.success(message)
          if (String(row.id) === String(user.userId)) await refreshOwnRoutes()
          await doRefresh(); return true
        } catch { if (valid()) Message.error(action === 'delete' ? '删除失败，请重试' : '重置 MCP Key 失败，请重试'); return false }
        finally { rowOperation.value = null; resume() }
      },
    })
    confirmation = handle
  }
  function onDelete(record: UserRecord) { confirmOperation(record, 'delete') }
  function onResetApiKey(record: UserRecord) { confirmOperation(record, 'key') }
  async function onSuperAdminChange(record: UserRecord, checked: string | number | boolean): Promise<boolean> {
    if (!available() || writeBusy.value) return false
    const current = guard(), row = copyUserRecord(record), nextValue = checked === true, session = sessionKey()
    const draft = createUserDraft(row); draft.is_super_admin = nextValue
    const payload = userUpdatePayload(row.id, draft)
    rowOperation.value = { id: row.id, action: 'super' }
    try {
      const response = await putUserInfo(payload)
      const message = userSuccess(response, '保存成功')
      if (session === sessionKey()) {
        needsList = true
        if (String(row.id) === String(user.userId)) pendingOwnSession = session
      }
      if (!current()) return false
      const target = rows.value.find(item => String(item.id) === String(row.id))
      if (target) target.is_super_admin = nextValue
      Message.success(message)
      if (String(row.id) === String(user.userId)) await refreshOwnRoutes()
      return current()
    } catch { if (current()) Message.error('修改超级管理员状态失败，请重试'); return false }
    finally { rowOperation.value = null; resume() }
  }
  async function onUserSaved(id: UserId | null): Promise<void> {
    if (!available()) return
    if (id !== null && String(id) === String(user.userId)) await refreshOwnRoutes()
    await doRefresh()
  }
  function onEditorCommitted(id: UserId | null, context: string) {
    if (context !== identityKey.value) return
    needsList = true
    if (id !== null && String(id) === String(user.userId)) pendingOwnSession = sessionKey()
  }
  function onEditorBusy(value: boolean) { editorSaving.value = value; if (!value) resume() }
  async function refreshOwnRoutes(): Promise<void> {
    if (!available() || routeRefreshing.value) return
    const key = sessionKey(), version = routeVersion
    const valid = () => available() && version === routeVersion && key === sessionKey()
    pendingOwnSession = null; routeRefreshing.value = true; routeRefreshError.value = ''
    try {
      await permission.initPermissionRoute(true, valid)
      if (valid() && !permission.hasPermission('system.user')) await router.replace('/index/home')
    } catch (loadFailure0) { if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), routeRefreshError.value = '用户已保存，但菜单刷新失败，请重试刷新菜单') }
    finally {
      if (!valid() && key === sessionKey()) pendingOwnSession = key
      routeRefreshing.value = false; resume()
    }
  }
  async function goToEmailConfig() {
    editor.value?.close(); closePassword()
    try { await router.push({ path: '/system/settings/index', query: { group: 'email' } }) }
    catch { if (available()) Message.error('邮箱配置页面打开失败，请重试') }
  }
  function pause() {
    contextVersion++; listRequests.invalidateRequests(); pendingList = null
    needsList = true; listLoading.value = false; editor.value?.close(); closePassword(); closeConfirmation()
  }
  function resume() {
    if (!available() || writeBusy.value) return
    if (pendingOwnSession === sessionKey()) { void refreshOwnRoutes(); return }
    pendingOwnSession = null
    if (needsList) void doRefresh()
  }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else { routeVersion++; pause() } }
  watch(identityKey, () => {
    pause(); rows.value = []; selectedRowKeys.value = []; resetConditions()
    pagination.page = 1; pagination.setTotalSize(0); listError.value = ''
    resume()
  }, { flush: 'sync' })
  watch(sessionKey, () => { routeVersion++; routeRefreshError.value = ''; pendingOwnSession = null }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; routeVersion++; pause() })
  onBeforeUnmount(() => { disposed = true; routeVersion++; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>
