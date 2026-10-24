<template>
  <TableBody ref="tableBody">
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
                <div class="mango-role-list__count">共 {{ table.dataList.length }} 条</div>
              </div>
              <a-button
                v-permission="'system.role:create'"
                :disabled="permissionPanel.saving"
                size="small"
                type="primary"
                @click="onAdd"
                data-testid="qa-views-system-role-button-新增"
              >
                新增
              </a-button>
            </div>

            <mango-panel-spin :loading="table.tableLoading.value">
              <div v-if="table.dataList.length" class="mango-role-list__body">
                <button
                  v-for="role in table.dataList"
                  :key="role.id"
                  type="button"
                  class="mango-role-item"
                  :class="{ 'mango-role-item--active': selectedRole?.id === role.id }"
                  :disabled="permissionPanel.saving"
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
                      v-permission="'system.role:edit'"
                      :disabled="isGuestRole(role) || permissionPanel.saving"
                      size="mini"
                      type="text"
                      @click="onUpdate(role)"
                      data-testid="qa-views-system-role-button-编辑"
                    >
                      编辑
                    </a-button>
                    <a-button
                      v-permission="'system.role:delete'"
                      :disabled="isGuestRole(role) || permissionPanel.saving"
                      size="mini"
                      status="danger"
                      type="text"
                      @click="onDelete(role)"
                      data-testid="qa-views-system-role-button-删除"
                    >
                      删除
                    </a-button>
                  </span>
                </button>
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
                v-permission="'system.role:edit'"
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

            <mango-panel-spin :loading="permissionPanel.loading">
              <template v-if="selectedRole && canReadPermission">
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
                {{ selectedRole ? '没有查看角色权限的权限' : '请选择左侧角色' }}
              </div>
            </mango-panel-spin>
          </section>
        </div>
      </div>
    </template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
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
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { getFormItems } from '@/utils/datacleaning'
  import { formItems } from './config'
  import usePermissionStore from '@/store/modules/permission'
  import useUserStore from '@/store/modules/user'
  import { useRouter } from 'vue-router'
  import {
    deleteUserRoleList,
    getUserRolePermission,
    getUserAllRole,
    postUserRoleList,
    putUserRolePermission,
    putUserRoleList,
  } from '@/api/user/role'

  const tableBody = ref()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const table = useTable()
  const formModel = ref({})
  const selectedRole = ref<any>(null)
  const homePermissionKey = 'index.home'
  const guestRoleName = '游客'
  const permissionStore = usePermissionStore()
  const userStore = useUserStore()
  const router = useRouter()
  const loadedRoleId = ref<number | null>(null)
  let permissionRequestId = 0

  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

  const permissionPanel = reactive({
    loading: false,
    saving: false,
    checkedKeys: [] as string[],
    expandedKeys: [] as string[],
    selectedKeys: [] as string[],
    treeData: [] as any[],
  })

  const selectedPage = computed(() => {
    const selectedKey = permissionPanel.selectedKeys[0]
    return selectedKey ? findPermissionNode(permissionPanel.treeData, selectedKey) : null
  })

  const selectedPageCount = computed(() => {
    const pageKeys = collectPageKeys(permissionPanel.treeData).filter((key) =>
      !findPermissionNode(permissionPanel.treeData, key)?.children?.length
    )
    return permissionPanel.checkedKeys.filter((key) => pageKeys.includes(key)).length
  })

  const selectedActionCount = computed(() => {
    const actionKeys = collectActionKeys(permissionPanel.treeData)
    return permissionPanel.checkedKeys.filter((key) => actionKeys.includes(key)).length
  })

  const selectedPageActionCount = computed(() => selectedPage.value?.actions?.length || 0)
  const pageCheckedKeys = computed(() => {
    const pageKeys = collectPageKeys(permissionPanel.treeData)
    return permissionPanel.checkedKeys.filter((key) => pageKeys.includes(key))
  })
  const isSelectedGuestRole = computed(() => isGuestRole(selectedRole.value))
  const canReadPermission = computed(() => permissionStore.hasPermission('system.role:detail'))
  const isPermissionReadonly = computed(() =>
    isSelectedGuestRole.value || !permissionStore.hasPermission('system.role:edit') ||
    permissionPanel.loading || permissionPanel.saving
  )
  const canSavePermission = computed(() =>
    canReadPermission.value && !isPermissionReadonly.value &&
    loadedRoleId.value !== null && loadedRoleId.value === selectedRole.value?.id
  )
  const readonlyTreeData = computed(() => {
    if (!isPermissionReadonly.value) return permissionPanel.treeData
    return markTreeCheckboxReadonly(permissionPanel.treeData)
  })

  function isGuestRole(role: any) {
    return role?.name === guestRoleName
  }

  function markTreeCheckboxReadonly(items: any[]): any[] {
    return items.map((item) => ({
      ...item,
      disableCheckbox: true,
      children: markTreeCheckboxReadonly(item.children || []),
    }))
  }

  function doRefresh() {
    table.tableLoading.value = true
    getUserAllRole()
      .then((res) => {
        table.dataList = (res.data || [])
          .map((role: any) => ({
            id: role.key,
            name: role.title,
            description: role.description,
          }))
          .sort((prev: any, next: any) => Number(isGuestRole(prev)) - Number(isGuestRole(next)))
        if (!selectedRole.value && table.dataList.length) {
          onSelectRole(table.dataList[0])
        } else if (selectedRole.value) {
          const freshRole = table.dataList.find((role) => role.id === selectedRole.value.id)
          if (freshRole) {
            selectedRole.value = freshRole
          } else {
            selectedRole.value = table.dataList[0] || null
            if (selectedRole.value) {
              onSelectRole(selectedRole.value)
            }
          }
        }
      })
      .catch(console.log)
      .finally(() => {
        table.tableLoading.value = false
      })
  }

  async function onSelectRole(role: any) {
    if (permissionPanel.saving) return
    const requestId = ++permissionRequestId
    selectedRole.value = role
    loadedRoleId.value = null
    permissionPanel.treeData = []
    permissionPanel.checkedKeys = []
    permissionPanel.selectedKeys = []
    permissionPanel.loading = false
    if (!canReadPermission.value) return
    permissionPanel.loading = true
    try {
      const res = await getUserRolePermission(role.id)
      if (requestId === permissionRequestId && selectedRole.value?.id === role.id) {
        permissionPanel.treeData = toPermissionTree(res.data?.tree || [])
        permissionPanel.checkedKeys = res.data?.checked_keys || []
        permissionPanel.expandedKeys = []
        permissionPanel.selectedKeys = [findFirstPageKey(permissionPanel.treeData)]
        loadedRoleId.value = role.id
      }
    } catch (error) {
      console.log(error)
    } finally {
      if (requestId === permissionRequestId) permissionPanel.loading = false
    }
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function onUpdate(item: any) {
    if (isGuestRole(item)) {
      Message.warning('游客角色为系统内置角色，仅支持查看')
      return
    }
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function onDelete(record: any) {
    if (isGuestRole(record)) {
      Message.warning('游客角色为系统内置角色，不允许删除')
      return
    }
    Modal.confirm({
      title: '提示',
      content: `是否要删除角色「${record.name}」？`,
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUserRoleList(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
      },
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      const value = getFormItems(formItems)
      if (data.isAdd) {
        postUserRoleList(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
        return
      }

      value.id = data.updateId
      putUserRoleList(value)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
        .finally(() => {
          modalDialogRef.value?.setConfirmLoading(false)
        })
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function toPermissionTree(items: any[]) {
    return (items || [])
      .map((item) => {
        const key = item.permissionKey || item.menuKey
        if (!key) return null
        return {
          key,
          title: item.menuName || item.permissionName || key,
          disabled: key === homePermissionKey,
          actions: item.actions || [],
          children: toPermissionTree(item.children || []),
        }
      })
      .filter(Boolean)
  }

  function collectTreeKeys(items: any[], keys: string[] = []) {
    items.forEach((item) => {
      keys.push(item.key)
      collectTreeKeys(item.children || [], keys)
    })
    return keys
  }

  function collectPageKeys(items: any[], keys: string[] = []) {
    items.forEach((item) => {
      keys.push(item.key)
      collectPageKeys(item.children || [], keys)
    })
    return keys
  }

  function collectActionKeys(items: any[], keys: string[] = []) {
    items.forEach((item) => {
      ;(item.actions || []).forEach((action: any) => keys.push(action.permissionKey))
      collectActionKeys(item.children || [], keys)
    })
    return keys
  }

  function findPermissionNode(items: any[], key: string): any {
    for (const item of items) {
      if (item.key === key) return item
      const child = findPermissionNode(item.children || [], key)
      if (child) return child
    }
    return null
  }

  function findParentKeys(items: any[], key: string, parents: string[] = []): string[] {
    for (const item of items) {
      if (item.key === key) return parents
      const childParents = findParentKeys(item.children || [], key, [...parents, item.key])
      if (childParents.length) return childParents
    }
    return []
  }

  function uniqKeys(keys: string[]) {
    return Array.from(new Set(keys))
  }

  function findFirstPageKey(items: any[]): string {
    return items[0]?.children?.[0]?.key || items[0]?.key || ''
  }

  function normalizeKeys(keys: unknown): string[] {
    return Array.isArray(keys) ? keys.map((key) => String(key)) : []
  }

  function expandPermissionTree(expanded: boolean) {
    permissionPanel.expandedKeys = expanded ? collectTreeKeys(permissionPanel.treeData) : []
  }

  function onPageSelect(keys: unknown) {
    permissionPanel.selectedKeys = normalizeKeys(keys)
  }

  function onPageCheck(keys: unknown, event?: any) {
    if (isSelectedGuestRole.value) return
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
        return (node?.actions || []).map((action: any) => action.permissionKey)
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
    if (isSelectedGuestRole.value) return
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

  function onSavePermission() {
    if (!selectedRole.value || !canSavePermission.value) return
    if (isSelectedGuestRole.value) {
      Message.warning('游客角色为系统内置角色，仅支持查看')
      return
    }
    permissionPanel.saving = true
    const roleId = selectedRole.value.id
    putUserRolePermission({
      role_id: roleId,
      permission_keys: [...permissionPanel.checkedKeys],
    })
      .then(async (res) => {
        permissionPanel.checkedKeys = res.data || permissionPanel.checkedKeys
        Message.success(res.msg)
        if (roleId === userStore.roleId) {
          await permissionStore.initPermissionRoute(true)
          if (!permissionStore.hasPermission('system.role')) await router.replace('/index/home')
        }
      })
      .catch(console.log)
      .finally(() => {
        permissionPanel.saving = false
      })
  }

  onMounted(() => {
    nextTick(() => {
      doRefresh()
    })
  })
</script>

<style scoped>
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
