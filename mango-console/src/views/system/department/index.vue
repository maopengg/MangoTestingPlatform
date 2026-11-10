<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader title="部门管理" />
    </template>
    <template #default>
      <TableTabs>
        <template #extra>
          <a-button
            size="small"
            type="primary"
            :disabled="writeBusy"
            @click="onAdd"
            data-testid="qa-views-system-department-button-新增"
          >
            新增
          </a-button>
        </template>
      </TableTabs>
      <a-table
        :scroll="{ x: tableScrollX }"
        :bordered="false"
        :columns="tableColumns"
        :data="rows"
        :loading="listLoading"
        :pagination="false"
        :rowKey="rowKey"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :model-value="record.status === 1"
                :loading="statusId === record.id"
                :disabled="writeBusy || editorVisible || scopeDrawer.visible"
                :before-change="(checked) => onStatusChange(record, checked)"
              />
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user_info?.name || record.update_user_info?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '范围', disabled: writeBusy, onClick: () => onScope(record) },
                  { label: '编辑', disabled: writeBusy, onClick: () => onUpdate(record) },
                  { label: '删除', danger: true, loading: deletingId === record.id, disabled: writeBusy, onClick: () => onDelete(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <ModalDialog modal-class="mango-simple-form-modal" ref="modalDialogRef" :title="actionTitle" :width="560" @confirm="onDataForm" @cancel="closeEditor">
    <template #content>
      <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal">
        <a-form-item class="mango-simple-form-item" label="部门名称" required>
          <a-input v-model="form.name" :disabled="saving" placeholder="请输入部门名称" />
        </a-form-item>
        <a-form-item class="mango-simple-form-item" label="状态">
          <a-switch v-model="form.status" :disabled="saving" :checked-value="1" :unchecked-value="0" />
        </a-form-item>
        <a-form-item class="mango-simple-form-item" label="部门描述">
          <a-textarea v-model="form.description" :disabled="saving" :auto-size="{ minRows: 3, maxRows: 5 }" placeholder="请输入部门描述" />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <a-drawer
    v-model:visible="scopeDrawer.visible"
    class="mango-department-scope-drawer"
    :width="620"
    @cancel="closeScope"
    unmount-on-close
  >
    <template #title>项目产品范围 - {{ scopeDrawer.departmentName }}</template>
    <div class="mango-department-scope-drawer__body">
      <a-spin :loading="scopeDrawer.loading">
        <template v-if="scopeDrawer.error"></template>
        <div v-else-if="scopeDrawer.ready && !scopeDrawer.products.length" class="mango-empty-state">暂无可选产品</div>
        <a-checkbox-group
          v-model="scopeDrawer.selectedProductIds"
          :disabled="!scopeDrawer.ready || scopeDrawer.loading || scopeDrawer.saving"
          class="mango-department-scope-list"
        >
          <a-checkbox
            v-for="product in scopeDrawer.products"
            :key="product.id"
            :value="product.id"
            class="mango-department-scope-item"
          >
            <span class="mango-department-scope-item__project">{{
              product.project?.name || '-'
            }}</span>
            <span class="mango-department-scope-item__product">{{ product.name }}</span>
          </a-checkbox>
        </a-checkbox-group>
      </a-spin>
    </div>
    <template #footer>
    <div class="mango-department-scope-drawer__footer">
      <a-button
        @click="closeScope"
        data-testid="qa-views-system-department-button-取消"
        >取消</a-button
      >
      <a-button
        type="primary"
        :loading="scopeDrawer.saving"
        :disabled="!scopeDrawer.ready || scopeDrawer.loading || (writeBusy && !scopeDrawer.saving)"
        @click="onSaveScope"
        data-testid="qa-views-system-department-button-保存"
        >保存</a-button
      >
    </div>
    </template>
  </a-drawer>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, onBeforeUnmount, onActivated, onDeactivated, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { usePagination, useRowKey } from '@/hooks/table'
  import type { ModalDialogType } from '@/types/components'
  import { deleteUserDepartment, getUserDepartment, getUserDepartmentProductScope, postUserDepartment, putUserDepartment, putUserDepartmentProductScope } from '@/api/user/department'
  import { getUserProduct } from '@/api/system/product'
  import { tableColumns, tableScrollX } from './config'
  import { createDepartmentForm, departmentId, departmentMessage, departmentSuccess, parseDepartments, parseDepartmentProducts, parseDepartmentScope, scopeSelection } from './department'
  import type { DepartmentId, DepartmentRow, DepartmentProduct } from './department'
  import TableTabs from '@/components/table/TableTabs.vue'

  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const rows = ref<DepartmentRow[]>([]), listLoading = ref(false), listError = ref('')
  const pagination = usePagination(doRefresh, listLoading), rowKey = useRowKey('id')
  const editorVisible = ref(false), editorId = ref<DepartmentId | null>(null), saving = ref(false)
  const form = reactive(createDepartmentForm())
  const actionTitle = computed(() => editorId.value === null ? '新增' : '编辑')
  const scopeDrawer = reactive<{ visible: boolean; loading: boolean; saving: boolean; ready: boolean; error: string; departmentId: DepartmentId | null; departmentName: string; products: DepartmentProduct[]; selectedProductIds: DepartmentId[] }>({
    visible: false, loading: false, saving: false, ready: false, error: '', departmentId: null, departmentName: '', products: [], selectedProductIds: [],
  })
  const statusId = ref<DepartmentId | null>(null), deletingId = ref<DepartmentId | null>(null)
  const writeBusy = computed(() => saving.value || scopeDrawer.saving || statusId.value !== null || deletingId.value !== null)
  let mounted = false, active = true, disposed = false, needsLoad = true
  let contextVersion = 0, listVersion = 0, editorVersion = 0, scopeVersion = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const identity = () => JSON.stringify([route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  function current(version: number, key: string) { return available() && version === contextVersion && key === identity() }

  async function doRefresh(): Promise<void> {
    if (!available()) { needsLoad = true; listLoading.value = false; return }
    const version = ++listVersion, context = contextVersion, key = identity()
    const page = pagination.page, pageSize = pagination.pageSize
    listLoading.value = true; listError.value = ''; needsLoad = false
    const valid = () => version === listVersion && current(context, key) && page === pagination.page && pageSize === pagination.pageSize
    try {
      const result = parseDepartments(await getUserDepartment({ page, pageSize }))
      if (!valid()) return
      rows.value = result.rows; pagination.setTotalSize(result.total)
      const lastPage = Math.max(1, Math.ceil(result.total / pageSize))
      if (page > lastPage) { pagination.page = lastPage; return doRefresh() }
    } catch (loadFailure0) {
      if (valid()) { rows.value = []; pagination.setTotalSize(0); (reportLoadError(loadFailure0, "部门加载失败，请重试", false), listError.value = '部门加载失败，请重试') }
    } finally { if (version === listVersion) listLoading.value = false }
  }
  function closeEditor() {
    editorVersion++; editorVisible.value = false; editorId.value = null
    Object.assign(form, createDepartmentForm()); void modalDialogRef.value?.close()
  }
  function openEditor(record: DepartmentRow | null) {
    if (!available() || writeBusy.value) return
    confirmation?.close(); confirmation = null
    closeScope(); editorVersion++; editorId.value = record?.id ?? null
    Object.assign(form, createDepartmentForm(record ?? undefined)); editorVisible.value = true
    void modalDialogRef.value?.show()
  }
  function onAdd() { openEditor(null) }
  function onUpdate(record: DepartmentRow) { openEditor(record) }
  async function onDataForm() {
    if (!available() || !editorVisible.value || writeBusy.value) { if (!saving.value) modalDialogRef.value?.setConfirmLoading(false); return }
    if (!form.name.trim() || (form.status !== 0 && form.status !== 1)) {
      Message.error('请输入部门名称并选择有效状态'); modalDialogRef.value?.setConfirmLoading(false); return
    }
    const draft = createDepartmentForm(form), id = editorId.value
    const generation = editorVersion, context = contextVersion, key = identity()
    saving.value = true
    let applied = false
    const valid = () => current(context, key) && editorVisible.value && generation === editorVersion
    try {
      const result = departmentSuccess(await (id === null ? postUserDepartment(draft) : putUserDepartment({ ...draft, id })))
      if (!valid()) return
      applied = true
      Message.success(departmentMessage(result, '保存成功')); closeEditor(); void doRefresh()
    } catch (error) { if (valid()) Message.error(departmentMessage(error, '保存失败，请重试')) }
    finally {
      saving.value = false
      if (generation === editorVersion) modalDialogRef.value?.setConfirmLoading(false)
      else if (!applied && !editorVisible.value) { needsLoad = true; resume() }
    }
  }
  async function onStatusChange(record: DepartmentRow, checked: boolean) {
    if (!available() || writeBusy.value || editorVisible.value || scopeDrawer.visible) return false
    const id = record.id, draft = { ...createDepartmentForm(record), id, status: checked ? 1 : 0 }
    const context = contextVersion, key = identity()
    statusId.value = id
    try {
      const result = departmentSuccess(await putUserDepartment(draft))
      if (!current(context, key)) return false
      const row = rows.value.find(row => String(row.id) === String(id))
      if (row) row.status = checked ? 1 : 0
      Message.success(departmentMessage(result, '保存成功')); void doRefresh()
      return true
    } catch (error) { if (current(context, key)) Message.error(departmentMessage(error, '状态更新失败，请重试')); return false }
    finally { statusId.value = null }
  }
  function onDelete(record: DepartmentRow) {
    if (!available() || writeBusy.value || confirmation || editorVisible.value || scopeDrawer.visible) return
    const id = record.id, context = contextVersion, key = identity()
    let closed = false
    const valid = () => !closed && confirmation === handle && current(context, key)
    const close = () => { closed = true; if (confirmation === handle) confirmation = null }
    const handle = Modal.confirm({ title: '提示', content: '是否要删除此部门？', cancelText: '取消', okText: '删除',
      onCancel: close,
      onBeforeOk: async () => {
        if (!valid() || writeBusy.value) return false
        deletingId.value = id
        try {
          const result = departmentSuccess(await deleteUserDepartment(id))
          if (!valid()) return false
          Message.success(departmentMessage(result, '删除成功')); close(); void doRefresh(); return true
        } catch (error) { if (valid()) Message.error(departmentMessage(error, '删除失败，请重试')); return false }
        finally { deletingId.value = null }
      },
    })
    confirmation = handle
  }
  function closeScope() {
    scopeVersion++
    Object.assign(scopeDrawer, { visible: false, loading: false, ready: false, error: '', departmentId: null, departmentName: '', products: [], selectedProductIds: [] })
  }
  function onScope(record: DepartmentRow) {
    if (!available() || writeBusy.value) return
    confirmation?.close(); confirmation = null
    closeEditor(); closeScope()
    Object.assign(scopeDrawer, { visible: true, departmentId: record.id, departmentName: record.name })
    void loadScope()
  }
  async function loadScope() {
    if (!available() || !scopeDrawer.visible || scopeDrawer.departmentId === null || scopeDrawer.saving) return
    const id = scopeDrawer.departmentId, generation = ++scopeVersion, context = contextVersion, key = identity()
    scopeDrawer.loading = true; scopeDrawer.ready = false; scopeDrawer.error = ''
    const valid = () => current(context, key) && generation === scopeVersion && scopeDrawer.visible && id === scopeDrawer.departmentId
    try {
      const [productResponse, scopeResponse] = await Promise.all([getUserProduct({}), getUserDepartmentProductScope(id)])
      const products = parseDepartmentProducts(productResponse), ids = parseDepartmentScope(scopeResponse)
      if (!valid()) return
      scopeDrawer.products = products; scopeDrawer.selectedProductIds = scopeSelection(ids, products); scopeDrawer.ready = true
    } catch (loadFailure1) { if (valid()) { scopeDrawer.products = []; scopeDrawer.selectedProductIds = []; (reportLoadError(loadFailure1, "项目产品范围加载失败，请重试", false), scopeDrawer.error = '项目产品范围加载失败，请重试') } }
    finally { if (generation === scopeVersion) scopeDrawer.loading = false }
  }
  async function onSaveScope() {
    if (!available() || !scopeDrawer.visible || !scopeDrawer.ready || scopeDrawer.loading || writeBusy.value || scopeDrawer.departmentId === null) return
    const id = scopeDrawer.departmentId, generation = scopeVersion, context = contextVersion, key = identity()
    const ids = scopeDrawer.selectedProductIds.map(departmentId)
    if (ids.some(id => id === null)) { Message.error('请选择有效产品'); return }
    const payload = { department_id: id, project_product_ids: ids.filter((id): id is DepartmentId => id !== null) }
    scopeDrawer.saving = true
    const valid = () => current(context, key) && generation === scopeVersion && scopeDrawer.visible
    try {
      const result = departmentSuccess(await putUserDepartmentProductScope(payload))
      if (!valid()) return
      Message.success(departmentMessage(result, '保存成功')); closeScope()
    } catch (error) { if (valid()) Message.error(departmentMessage(error, '范围保存失败，请重试')) }
    finally { scopeDrawer.saving = false }
  }
  function pause() {
    contextVersion++; listVersion++; needsLoad = true; listLoading.value = false
    closeEditor(); closeScope(); confirmation?.close(); confirmation = null
  }
  function resume() { if (available() && needsLoad) void doRefresh() }
  function onVisibility() { if (document.visibilityState !== 'visible') pause(); else resume() }
  watch(identity, () => { pause(); rows.value = []; pagination.setTotalSize(0); pagination.page = 1; resume() }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', onVisibility); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', onVisibility) })
</script>

<style scoped>
  .mango-department-scope-drawer__body {
    min-height: 80px;
  }

  .mango-department-error {
    color: var(--m-danger);
    padding: var(--m-page-gap);
  }

  .mango-department-scope-list {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .mango-department-scope-item {
    display: flex;
    width: 100%;
    min-height: 36px;
    align-items: center;
    padding: 6px 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-department-scope-item__project {
    color: var(--m-muted);
    margin-right: 8px;
  }

  .mango-department-scope-item__product {
    font-weight: 500;
  }

  .mango-department-scope-drawer__footer {
    display: flex;
    justify-content: flex-start;
    gap: 8px;

  }
</style>
