<template>
  <TableBody>
    <template #header>
      <TableHeader title="角色管理" />
    </template>

    <template #default>
      <div class="mango-workbench-scroll-x mango-role-workbench-scroll">
        <div class="mango-role-workbench">
          <section class="mango-role-list">
            <div class="mango-role-list__header">
              <div>
                <div class="mango-role-list__title">角色</div>
                <div class="mango-role-list__count">共 {{ roles.length }} 条</div>
              </div>
              <a-button

                :disabled="writeBusy"
                size="small"
                type="primary"
                @click="onAdd"
                data-testid="qa-views-system-role-button-新增"
              >
                新增
              </a-button>
            </div>

            <mango-panel-spin :loading="listLoading">
              <template v-if="listError"></template>
              <div v-else-if="roles.length" class="mango-role-list__body">
                <div
                  v-for="role in roles"
                  :key="role.id"
                  role="button"
                  tabindex="0"
                  class="mango-role-item"
                  :class="{ 'mango-role-item--active': selectedRole?.id === role.id }"
                  :aria-disabled="writeBusy || editorVisible"
                  @keydown.enter.self.prevent="onSelectRole(role)"
                  @keydown.space.self.prevent="onSelectRole(role)"
                  @click="onSelectRole(role)"
                >
                  <span class="mango-role-item__main">
                    <span class="mango-role-item__name">{{ role.name }}</span>
                    <span class="mango-role-item__desc">
                      {{ role.description ? `描述：${role.description}` : '暂无描述' }}
                    </span>
                  </span>
                  <span class="mango-role-item__ops" @click.stop>
                    <a-button

                      :disabled="isGuestRole(role) || writeBusy"
                      size="mini"
                      type="text"
                      @click="onUpdate(role)"
                      data-testid="qa-views-system-role-button-编辑"
                    >
                      编辑
                    </a-button>
                    <a-button

                      :disabled="isGuestRole(role) || writeBusy"
                      size="mini"
                      status="danger"
                      type="text"
                      @click="onDelete(role)"
                      data-testid="qa-views-system-role-button-删除"
                    >
                      删除
                    </a-button>
                  </span>
                </div>
              </div>
              <div v-else class="mango-empty-state">暂无角色</div>
            </mango-panel-spin>
          </section>

          <section class="mango-role-permission">
            <div class="mango-role-permission__header">
              <div>
                <div class="mango-role-permission__title">
                  {{ selectedRole?.name || '选择角色后配置权限' }}
                </div>
                <div class="mango-role-permission__desc">
                  {{
                    selectedRole?.description || '左侧选择一个角色，配置它可以访问的页面和操作。'
                  }}
                </div>
              </div>
              <a-button

                v-if="selectedRole"
                size="small"
                type="primary"
                :disabled="!canSavePermission"
                :loading="permissionPanel.saving"
                @click="onSavePermission"
                data-testid="qa-views-system-role-button-保存权限"
              >
                保存权限
              </a-button>
            </div>

            <div v-if="routeRefreshError" class="mango-role-error" role="alert">{{ routeRefreshError }} <a-button size="small" :loading="routeRefreshing" :disabled="writeBusy" @click="refreshOwnRoutes">刷新菜单</a-button></div>
            <mango-panel-spin :loading="permissionPanel.loading">
              <div v-if="permissionError" :class="{ 'mango-role-error': !permissionLoadFailed }">
                <span v-if="!permissionLoadFailed" role="alert">{{ permissionError }}</span>
                <a-button size="small" :loading="permissionPanel.loading" :disabled="writeBusy" @click="retryPermission">重新加载</a-button>
              </div>
              <template v-else-if="selectedRole">
                <div class="mango-permission-summary">
                  <div>
                    <span class="mango-permission-summary__label">已选页面</span>
                    <span class="mango-permission-summary__value">{{ selectedPageCount }}</span>
                  </div>
                  <div>
                    <span class="mango-permission-summary__label">已选操作</span>
                    <span class="mango-permission-summary__value">{{ selectedActionCount }}</span>
                  </div>
                  <a-tag color="blue" size="small">首页默认开放</a-tag>
                </div>

                <div class="mango-permission-layout">
                  <section class="mango-permission-panel mango-permission-panel--tree">
                    <div class="mango-permission-panel__header">
                      <span>页面权限</span>
                      <a-space>
                        <a-button
                          size="mini"
                          @click="expandPermissionTree(true)"
                          data-testid="qa-views-system-role-button-展开"
                          >展开</a-button
                        >
                        <a-button
                          size="mini"
                          @click="expandPermissionTree(false)"
                          data-testid="qa-views-system-role-button-收起"
                          >收起</a-button
                        >
                      </a-space>
                    </div>
                    <a-tree
                      :checked-keys="pageCheckedKeys"
                      v-model:expanded-keys="permissionPanel.expandedKeys"
                      v-model:selected-keys="permissionPanel.selectedKeys"
                      :data="readonlyTreeData"
                      checkable
                      block-node
                      @check="onPageCheck"
                      @select="onPageSelect"
                    />
                  </section>

                  <section class="mango-permission-panel">
                    <div class="mango-permission-panel__header">
                      <span>操作列表</span>
                      <span class="mango-permission-panel__sub">
                        {{ selectedPage?.title || '未选择页面' }} · {{ selectedPageActionCount }} 项
                      </span>
                    </div>
                    <div v-if="selectedPage" class="mango-permission-actions">
                      <a-alert v-if="selectedPage.key === homePermissionKey" type="info" show-icon>
                        首页是登录后的基础权限，所有角色默认拥有。
                      </a-alert>
                      <template v-if="selectedPage.actions?.length">
                        <a-checkbox
                          v-for="action in selectedPage.actions"
                          :key="action.permissionKey"
                          :model-value="permissionPanel.checkedKeys.includes(action.permissionKey)"
                          :disabled="
                            isPermissionReadonly || permissionPanel.loading || permissionPanel.saving ||
                            !permissionPanel.checkedKeys.includes(selectedPage.key)
                          "
                          @change="(checked) => onActionCheck(action.permissionKey, checked)"
                        >
                          <span class="mango-permission-action__content">
                            <span class="mango-permission-action__name">{{
                              action.permissionName
                            }}</span>
                            <span class="mango-permission-action__desc">
                              {{ action.permissionDescription || '当前操作暂无描述' }}
                            </span>
                          </span>
                        </a-checkbox>
                      </template>
                      <div v-else class="mango-empty-state">当前页面没有可单独授权的操作</div>
                    </div>
                    <div v-else class="mango-empty-state">请选择左侧页面</div>
                  </section>
                </div>
              </template>
              <div v-else class="mango-empty-state">
                请选择左侧角色
              </div>
            </mango-panel-spin>
          </section>
        </div>
      </div>
    </template>
  </TableBody>

  <ModalDialog modal-class="mango-simple-form-modal" ref="modalDialogRef" :title="actionTitle" :width="560" @confirm="onDataForm" @cancel="closeEditor">
    <template #content>
      <a-form auto-label-width layout="horizontal" class="mango-simple-form" :model="form" :disabled="saving">
        <a-form-item class="mango-simple-form-item"
          v-for="item of roleFormFields"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="form[item.key]" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="form[item.key]"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              :placeholder="item.placeholder"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, onActivated, onDeactivated, onBeforeUnmount, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import type { ModalDialogType } from '@/types/components'
  import { roleFormFields, roleEditorWidth } from './config'
  import { collectTreeKeys, collectPageKeys, collectActionKeys, findPermissionNode, findParentKeys, uniqKeys, normalizeKeys, findFirstPageKey, markTreeCheckboxReadonly, homePermissionKey, isGuestRole, createRoleForm, parseRoles, parseRolePermissions, parsePermissionKeys, roleSuccess, roleMessage } from './role-permissions'
  import type { RoleId, RoleRow, PermissionNode, PageCheckEvent } from './role-permissions'
  import usePermissionStore from '@/store/modules/permission'
  import useUserStore from '@/store/modules/user'
  import { useRoute, useRouter } from 'vue-router'
  import { deleteUserRoleList, getUserRolePermission, getUserAllRole, postUserRoleList, putUserRolePermission, putUserRoleList } from '@/api/user/role'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const roles = ref<RoleRow[]>([]), listLoading = ref(false), listError = ref(''), permissionError = ref('')
  const permissionLoadFailed = ref(false)
  const selectedRole = ref<RoleRow | null>(null), loadedRoleId = ref<RoleId | null>(null)
  const permissionStore = usePermissionStore(), userStore = useUserStore(), router = useRouter(), route = useRoute()
  const pagePath = route.path
  const form = reactive(createRoleForm()), editorId = ref<RoleId | null>(null), editorVisible = ref(false), saving = ref(false), deletingId = ref<RoleId | null>(null)
  const actionTitle = computed(() => editorId.value === null ? '新增' : '编辑')
  const permissionPanel = reactive<{ loading: boolean; saving: boolean; checkedKeys: string[]; expandedKeys: string[]; selectedKeys: string[]; treeData: PermissionNode[] }>({
    loading: false, saving: false, checkedKeys: [], expandedKeys: [], selectedKeys: [], treeData: [],
  })
  const routeRefreshing = ref(false), routeRefreshError = ref('')
  const writeBusy = computed(() => saving.value || deletingId.value !== null || permissionPanel.saving || routeRefreshing.value)
  const selectedPage = computed(() => findPermissionNode(permissionPanel.treeData, permissionPanel.selectedKeys[0] || ''))
  const selectedPageCount = computed(() => permissionPanel.checkedKeys.filter(key => collectPageKeys(permissionPanel.treeData).filter(key => !findPermissionNode(permissionPanel.treeData, key)?.children.length).includes(key)).length)
  const selectedActionCount = computed(() => permissionPanel.checkedKeys.filter(key => collectActionKeys(permissionPanel.treeData).includes(key)).length)
  const selectedPageActionCount = computed(() => selectedPage.value?.actions.length || 0)
  const pageCheckedKeys = computed(() => permissionPanel.checkedKeys.filter(key => collectPageKeys(permissionPanel.treeData).includes(key)))
  const isSelectedGuestRole = computed(() => isGuestRole(selectedRole.value))
  const isPermissionReadonly = computed(() => isSelectedGuestRole.value || permissionPanel.loading || writeBusy.value || editorVisible.value || loadedRoleId.value === null)
  const canSavePermission = computed(() => !isPermissionReadonly.value && loadedRoleId.value === selectedRole.value?.id)
  const readonlyTreeData = computed(() => isPermissionReadonly.value ? markTreeCheckboxReadonly(permissionPanel.treeData) : permissionPanel.treeData)
  let mounted = false, active = true, disposed = false, needsLoad = true
  let contextVersion = 0, listVersion = 0, permissionRequestId = 0, editorVersion = 0
  let routeEpoch = 0, pendingRouteSession: string | null = null
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  let listPending: Promise<void> | null = null
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const sessionKey = () => JSON.stringify([route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment])
  const identity = () => JSON.stringify([sessionKey(), permissionStore.permissionKeys])
  const current = (version: number, key: string) => available() && version === contextVersion && key === identity()
  function clearPermissions() {
    permissionRequestId++; loadedRoleId.value = null; permissionError.value = ''
    permissionLoadFailed.value = false
    Object.assign(permissionPanel, { loading: false, checkedKeys: [], expandedKeys: [], selectedKeys: [], treeData: [] })
  }
  function doRefresh(): Promise<void> {
    if (!available()) { needsLoad = true; return Promise.resolve() }
    if (listPending) return listPending
    const version = ++listVersion, context = contextVersion, key = identity()
    const valid = () => version === listVersion && current(context, key)
    listLoading.value = true; listError.value = ''; needsLoad = false
    const pending = (async () => {
      try {
        const result = parseRoles(await getUserAllRole())
        if (!valid()) return
        roles.value = result
        const previous = selectedRole.value
        const next = result.find(role => String(role.id) === String(previous?.id)) || result[0] || null
        selectedRole.value = next
        if (!next) clearPermissions()
        else if (!previous || previous.id !== next.id || loadedRoleId.value === null) { clearPermissions(); void onSelectRole(next) }
      } catch (error) {
        if (valid()) { roles.value = []; selectedRole.value = null; clearPermissions(); (reportLoadError(error, "角色加载失败，请重试", false), listError.value = roleMessage(error, '角色加载失败，请重试')) }
      } finally { if (valid()) listLoading.value = false }
    })()
    listPending = pending
    void pending.finally(() => { if (listPending === pending) listPending = null })
    return pending
  }
  async function onSelectRole(role: RoleRow): Promise<void> {
    if (!available() || writeBusy.value || editorVisible.value) return
    clearPermissions(); selectedRole.value = role
    const requestId = permissionRequestId, context = contextVersion, key = identity(), id = role.id
    const valid = () => requestId === permissionRequestId && current(context, key) && selectedRole.value?.id === id
    permissionPanel.loading = true
    try {
      const result = parseRolePermissions(await getUserRolePermission(id))
      if (!valid()) return
      permissionPanel.treeData = result.tree; permissionPanel.checkedKeys = result.checkedKeys
      permissionPanel.selectedKeys = [findFirstPageKey(result.tree)]; loadedRoleId.value = id
    } catch (error) {
      if (valid()) {
        reportLoadError(error, '权限加载失败，请重试')
        permissionLoadFailed.value = true
        permissionError.value = roleMessage(error, '权限加载失败，请重试')
      }
    }
    finally { if (valid()) permissionPanel.loading = false }
  }
  function retryPermission() { if (selectedRole.value) return onSelectRole(selectedRole.value) }
  function closeEditor() {
    editorVersion++; editorVisible.value = false; editorId.value = null
    Object.assign(form, createRoleForm()); void modalDialogRef.value?.close()
  }
  function openEditor(role: RoleRow | null) {
    if (!available() || writeBusy.value) return
    if (isGuestRole(role)) { Message.warning('游客角色为系统内置角色，仅支持查看'); return }
    confirmation?.close(); confirmation = null; editorVersion++
    editorId.value = role?.id ?? null; Object.assign(form, createRoleForm(role ?? undefined)); editorVisible.value = true
    void modalDialogRef.value?.show()
  }
  function onAdd() { openEditor(null) }
  function onUpdate(role: RoleRow) { openEditor(role) }
  async function onDataForm(): Promise<void> {
    if (!available() || !editorVisible.value || writeBusy.value) { if (!saving.value) modalDialogRef.value?.setConfirmLoading(false); return }
    if (!form.name.trim()) { Message.error('请输入角色名称'); modalDialogRef.value?.setConfirmLoading(false); return }
    const draft = createRoleForm(form), id = editorId.value, generation = editorVersion, context = contextVersion, key = identity()
    const valid = () => current(context, key) && editorVisible.value && generation === editorVersion
    saving.value = true
    try {
      const result = roleSuccess(await (id === null ? postUserRoleList(draft) : putUserRoleList({ ...draft, id })))
      if (!valid()) return
      Message.success(roleMessage(result, '保存成功')); closeEditor(); invalidateList(); needsLoad = true
    } catch (error) { if (valid()) Message.error(roleMessage(error, '保存失败，请重试')) }
    finally {
      saving.value = false
      if (generation === editorVersion) modalDialogRef.value?.setConfirmLoading(false)
      if (!valid()) { invalidateList(); needsLoad = true }
      resume()
    }
  }
  function onDelete(role: RoleRow) {
    if (!available() || writeBusy.value || editorVisible.value || confirmation) return
    if (isGuestRole(role)) { Message.warning('游客角色为系统内置角色，不允许删除'); return }
    const id = role.id, context = contextVersion, key = identity()
    let closed = false
    const valid = () => !closed && confirmation === handle && current(context, key)
    const close = () => { closed = true; if (confirmation === handle) confirmation = null }
    const handle = Modal.confirm({ title: '提示', content: `是否要删除角色「${role.name}」？`, cancelText: '取消', okText: '删除',
      onCancel: close,
      onBeforeOk: async () => {
        if (!valid() || writeBusy.value) return false
        deletingId.value = id
        try {
          const result = roleSuccess(await deleteUserRoleList(id))
          if (!valid()) return false
          Message.success(roleMessage(result, '删除成功')); close(); invalidateList(); needsLoad = true; return true
        } catch (error) { if (valid()) Message.error(roleMessage(error, '删除失败，请重试')); return false }
        finally { deletingId.value = null; if (!valid()) { invalidateList(); needsLoad = true }; resume() }
      },
    })
    confirmation = handle
  }
  function expandPermissionTree(expanded: boolean) {
    permissionPanel.expandedKeys = expanded ? collectTreeKeys(permissionPanel.treeData) : []
  }

  function onPageSelect(keys: unknown) {
    permissionPanel.selectedKeys = normalizeKeys(keys)
  }

  function onPageCheck(keys: unknown, event?: PageCheckEvent) {
    if (!available() || isPermissionReadonly.value) return
    const checkedPageKeys = normalizeKeys(keys)
    const pageKeys = collectPageKeys(permissionPanel.treeData)
    const actionKeys = collectActionKeys(permissionPanel.treeData)
    let checkedActionKeys: string[] = []
    let uncheckedPageKeys: string[] = []
    if (event?.checked === true && event?.node?.key) {
      const checkedNode = findPermissionNode(permissionPanel.treeData, String(event.node.key))
      checkedActionKeys = checkedNode ? collectActionKeys([checkedNode]) : []
    } else if (event?.checked === false && event?.node?.key) {
      const uncheckedNode = findPermissionNode(permissionPanel.treeData, String(event.node.key))
      uncheckedPageKeys = uncheckedNode
        ? collectPageKeys([uncheckedNode])
        : [String(event.node.key)]
    } else if (!event) {
      const previousPageKeys = permissionPanel.checkedKeys.filter((key) => pageKeys.includes(key))
      const newlyCheckedPageKeys = checkedPageKeys.filter((key) => !previousPageKeys.includes(key))
      checkedActionKeys = newlyCheckedPageKeys.flatMap((key) => {
        const node = findPermissionNode(permissionPanel.treeData, key)
        return (node?.actions || []).map((action) => action.permissionKey)
      })
      uncheckedPageKeys = previousPageKeys.filter((key) => !checkedPageKeys.includes(key))
    }
    const keptActionKeys = permissionPanel.checkedKeys.filter((key) => {
      if (!actionKeys.includes(key)) return false
      const pageKey = key.split(':')[0]
      return !uncheckedPageKeys.includes(pageKey)
    })
    permissionPanel.checkedKeys = uniqKeys([
      ...checkedPageKeys,
      ...keptActionKeys,
      ...checkedActionKeys,
      homePermissionKey,
    ])
  }

  function onActionCheck(actionKey: string, checked: boolean | (string | number | boolean)[]) {
    if (!available() || isPermissionReadonly.value) return
    const pageKey = actionKey.split(':')[0]
    const parentKeys = findParentKeys(permissionPanel.treeData, pageKey)
    if (checked === true) {
      permissionPanel.checkedKeys = uniqKeys([
        ...permissionPanel.checkedKeys,
        ...parentKeys,
        pageKey,
        actionKey,
        homePermissionKey,
      ])
      return
    }
    permissionPanel.checkedKeys = permissionPanel.checkedKeys.filter((key) => key !== actionKey)
  }

  async function refreshOwnRoutes(): Promise<void> {
    if (!available() || routeRefreshing.value) return
    const key = sessionKey(), epoch = routeEpoch
    const valid = () => available() && epoch === routeEpoch && key === sessionKey()
    pendingRouteSession = null
    routeRefreshing.value = true; routeRefreshError.value = ''
    try {
      await permissionStore.initPermissionRoute(true, valid)
      if (valid() && !permissionStore.hasPermission('system.role')) await router.replace('/index/home')
    } catch (loadFailure0) { if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), routeRefreshError.value = '权限已保存，但菜单刷新失败，请重试刷新菜单') }
    finally {
      if (!valid() && key === sessionKey()) pendingRouteSession = key
      routeRefreshing.value = false; resume()
    }
  }
  async function onSavePermission(): Promise<void> {
    if (!available() || !selectedRole.value || !canSavePermission.value) return
    const roleId = selectedRole.value.id, keys = [...permissionPanel.checkedKeys]
    const context = contextVersion, key = identity(), session = sessionKey(), generation = permissionRequestId
    const valid = () => current(context, key) && generation === permissionRequestId && selectedRole.value?.id === roleId
    permissionPanel.saving = true
    let succeeded = false
    try {
      const result = roleSuccess(await putUserRolePermission({ role_id: roleId, permission_keys: keys }))
      if (!valid()) {
        if (session === sessionKey() && String(roleId) === String(userStore.roleId)) pendingRouteSession = session
        return
      }
      succeeded = true
      // The write has succeeded even if its receipt or subsequent route refresh cannot be read.
      try { permissionPanel.checkedKeys = parsePermissionKeys(result.data) }
      catch { clearPermissions(); permissionError.value = '权限已保存，回执格式异常，请重新读取权限' }
      Message.success(roleMessage(result, '保存成功'))
      if (session === sessionKey() && String(roleId) === String(userStore.roleId)) await refreshOwnRoutes()
    } catch (error) { if (valid()) Message.error(roleMessage(error, '权限保存失败，请重试')) }
    finally {
      permissionPanel.saving = false
      if (!valid() && !succeeded) { invalidateList(); needsLoad = true }
      resume()
    }
  }
  function invalidateList() { listVersion++; listPending = null; listLoading.value = false }
  function pause(preserveRouteRefresh = false) {
    if (!preserveRouteRefresh) routeEpoch++
    contextVersion++; invalidateList(); clearPermissions(); needsLoad = true
    closeEditor(); confirmation?.close(); confirmation = null
  }
  function resume() {
    if (!available()) return
    if (pendingRouteSession === sessionKey() && !writeBusy.value) { void refreshOwnRoutes(); return }
    if (needsLoad) void doRefresh()
    else if (selectedRole.value && loadedRoleId.value === null && !permissionPanel.loading && !permissionError.value && !writeBusy.value && !editorVisible.value) void retryPermission()
  }
  function onVisibility() { if (document.visibilityState !== 'visible') pause(); else resume() }
  let previousSession = sessionKey()
  watch(identity, () => {
    const sessionChanged = previousSession !== sessionKey()
    if (sessionChanged) { previousSession = sessionKey(); routeRefreshError.value = ''; pendingRouteSession = null }
    pause(!sessionChanged); roles.value = []; selectedRole.value = null; resume()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', onVisibility); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', onVisibility) })
</script>


<style scoped>
  .mango-role-error { padding: var(--m-page-gap); color: var(--m-danger); }

  .mango-role-workbench {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: var(--m-page-gap);
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-role-workbench-scroll {
    --mango-workbench-min-width: 1130px;
    margin-top: var(--m-page-gap);
  }

  .mango-role-workbench-scroll > .mango-role-workbench {
    min-width: var(--mango-workbench-min-width);
  }

  .mango-role-list,
  .mango-role-permission,
  .mango-permission-panel {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-role-list {
    display: flex;
    min-height: 0;
    overflow: hidden;
    flex-direction: column;
  }

  .mango-role-list :deep(> .arco-spin),
  .mango-role-list :deep(> .arco-spin > .mango-panel-spin__content) {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
  }

  .mango-role-list__header,
  .mango-role-permission__header,
  .mango-permission-panel__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-role-list__header {
    min-height: 56px;
    padding: 0 12px;
  }

  .mango-role-list__title,
  .mango-role-permission__title,
  .mango-permission-panel__header {
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-role-list__title,
  .mango-role-permission__title {
    font-size: 14px;
  }

  .mango-role-list__count,
  .mango-role-permission__desc,
  .mango-permission-panel__sub,
  .mango-role-item__desc {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-role-list__body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 10px;
  }

  .mango-role-item {
    display: flex;
    width: 100%;
    min-height: 64px;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin: 0 0 8px;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    cursor: pointer;
    text-align: left;
    transition: background 0.18s ease, border-color 0.18s ease;
  }

  .mango-role-item:hover {
    border-color: var(--m-border);
    background: var(--m-surface-soft);
  }

  .mango-role-item:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 2px;
  }

  .mango-role-item--active {
    border-color: var(--m-primary-border);
    background: var(--m-primary-soft);
  }

  .mango-role-item__main {
    display: flex;
    min-width: 0;
    flex: 1;
    flex-direction: column;
    gap: 4px;
  }

  .mango-role-item__name,
  .mango-role-item__desc {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-role-item__name {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  .mango-role-item__ops {
    display: flex;
    flex-shrink: 0;
    gap: 2px;
  }

  .mango-role-permission {
    display: flex;
    min-width: 0;
    min-height: 0;
    height: 100%;
    overflow: hidden;
    flex-direction: column;
  }

  .mango-role-permission :deep(> .arco-spin),
  .mango-role-permission :deep(> .arco-spin > .mango-panel-spin__content) {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
  }

  .mango-role-permission__header {
    min-height: 64px;
    padding: 0 14px;
  }

  .mango-permission-summary {
    display: flex;
    align-items: center;
    gap: 16px;
    margin: 12px;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-permission-summary__label {
    margin-right: 6px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-permission-summary__value {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
  }

  .mango-permission-layout {
    display: grid;
    grid-template-columns: minmax(420px, 1fr) minmax(360px, 0.85fr);
    gap: var(--m-page-gap);
    flex: 1;
    min-height: 0;
    padding: 0 12px 12px;
  }

  .mango-permission-panel {
    display: flex;
    min-height: 0;
    overflow: hidden;
    flex-direction: column;
  }

  .mango-permission-panel--tree {
    overflow: hidden;
  }

  .mango-permission-panel--tree :deep(.arco-tree) {
    flex: 1;
    height: auto;
    min-height: 0;
    overflow: auto;
    padding: 6px 8px 10px;
  }

  .mango-permission-panel--tree :deep(.arco-tree-node),
  .mango-permission-panel--tree :deep(.arco-tree-node-title-block),
  .mango-permission-panel--tree :deep(.arco-tree-node-title) {
    width: 100%;
  }

  .mango-permission-panel__header {
    min-height: 42px;
    padding: 0 12px;
    font-size: 13px;
  }

  .mango-permission-panel__sub {
    font-weight: 400;
  }

  .mango-permission-actions {
    display: grid;
    grid-template-columns: 1fr;
    align-content: start;
    flex: 1;
    min-height: 0;
    overflow: auto;
    gap: 10px 12px;
    padding: 12px;
  }

  .mango-permission-actions :deep(.arco-alert) {
    grid-column: 1 / -1;
  }

  .mango-permission-actions :deep(.arco-checkbox) {
    min-height: 56px;
    margin-left: 0;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-permission-actions :deep(.arco-checkbox-label) {
    min-width: 0;
    flex: 1;
  }

  .mango-permission-action__content {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 3px;
    line-height: 1.35;
  }

  .mango-permission-action__name {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  .mango-permission-action__desc {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  @media (max-width: 960px) {
    .mango-role-workbench {
      height: auto;
      min-height: 0;
      overflow: visible;
      grid-template-columns: 1fr;
    }

    .mango-permission-layout {
      grid-template-columns: 1fr;
    }

    .mango-permission-panel--tree :deep(.arco-tree) {
      max-height: 300px;
    }
  }
</style>
