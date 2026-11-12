<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header><TableHeader title="页面步骤" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        show-modules
        :model-value="projectProduct"
        :module-value="selectedModule"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item in headerConditionItems" :key="item.key" :label="item.label">
              <a-input
                v-if="item.type === 'input'"
                v-model="item.value"
                :placeholder="item.placeholder"
                allow-clear
                @blur="onSearch"
                @clear="onSearch"
              />
              <a-select
                v-else-if="item.key === 'page_id'"
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="pageOptions"
                :loading="pagesLoading"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                @change="onSearch"
              />
              <a-select
                v-else-if="item.key === 'status'"
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="statusOptions"
                :loading="enumsLoading"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                @change="onSearch"
              />
              <a-select
                v-else-if="item.key === 'update_user'"
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="userOptions"
                :loading="usersLoading"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                value-key="key"
                @change="onSearch"
              />
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-button
              type="primary"
              size="small"
              :disabled="editingBusy || deleting"
              data-testid="qa-views-uitest-page-steps-button-新增"
              @click="onAdd"
              >新增</a-button
            >
            <a-button
              status="danger"
              size="small"
              :loading="deleting"
              :disabled="editingBusy || !selectedRowKeys.length"
              data-testid="qa-views-uitest-page-steps-button-批量删除"
              @click="onDelete(null)"
              >批量删除</a-button
            >
          </a-space>
        </template>
        <div class="mango-ui-step-list-body">
          
          
          
          
          <MangoRequestFeedback v-if="actionError" :message="(actionError)" />
          <a-table
            class="mango-native-scroll-table mango-ui-step-list-table"
            :bordered="false"
            :row-selection="{ selectedRowKeys, showCheckedAll: true }"
            :loading="listLoading"
            :data="rows"
            :pagination="false"
            row-key="id"
            :scroll="{ x: TABLE_SCROLL_X, y: '100%' }"
            @selection-change="onSelectionChange"
          >
            <template #columns>
              <a-table-column
                v-for="item in tableColumns"
                :key="item.key"
                :align="item.align"
                :title="item.title"
                :width="item.width"
                :data-index="item.key"
                :fixed="item.fixed"
                :ellipsis="item.ellipsis"
                :tooltip="item.tooltip"
              >
                <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
                <template v-else-if="item.key === 'page'" #cell="{ record }">{{
                  record.page?.name || '-'
                }}</template>
                <template v-else-if="item.key === 'status'" #cell="{ record }"
                  ><a-tag :color="enumStore.status_colors[record.status]" size="small">{{
                    enumStore.task_status[record.status]?.title || '-'
                  }}</a-tag></template
                >
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">{{
                  formatProjectProductPath(record.project_product)
                }}</template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">{{
                  formatModulePath(record.module)
                }}</template>
                <template v-else-if="item.key === 'update_user'" #cell="{ record }">{{
                  record.update_user?.name || record.update_user?.username || '-'
                }}</template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
                      {
                        label: '调试',
                        loading: runningId !== null && String(runningId) === String(record.id),
                        disabled: runningId !== null || listLoading,
                        onClick: () => onRunCase(record),
                      },
                      { label: '步骤', disabled: listLoading, onClick: () => onSteps(record) },
                      { label: '用例', disabled: listLoading, onClick: () => onReferences(record) },
                      {
                        label: '编辑',
                        disabled: editingBusy || deleting || listLoading,
                        onClick: () => onUpdate(record),
                      },
                      {
                        label: '删除',
                        danger: true,
                        loading: deletingIds.has(String(record.id)),
                        disabled: editingBusy || deleting || listLoading,
                        onClick: () => onDelete(record),
                      },
                    ]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </div>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <StepEditor
    ref="editorRef"
    @saved="onSaved"
    @reconcile="doRefresh(false)"
    @busy-change="editingBusy = $event"
  />
  <StepReferencesPanel ref="referencesRef" />
</template>
<script setup lang="ts">
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import { computed, onMounted, ref, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { getUiSteps, deleteUiSteps, getUiStepsTest } from '@/api/uitest/page-steps'
  import { getUiPageName } from '@/api/uitest/page'
  import { getUserName } from '@/api/user/user'
  import { usePagination } from '@/hooks/table'
  import { usePagePolling, isPendingExecution } from '@/hooks/use-page-polling'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePageData } from '@/store/page-data'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { getFormItems } from '@/utils/datacleaning'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import { fieldNames } from '@/setting'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import StepEditor from './components/StepEditor.vue'
  import StepReferencesPanel from './components/StepReferencesPanel.vue'
  import { createConditionItems, tableColumns, TABLE_SCROLL_X } from './config'
  import {
    stepListId,
    stepOptionId,
    stepListQuery,
    stepListResponse,
    readStepList,
    readStepOptions,
    readStepListRow,
    type StepListRow,
    type StepListId,
    type StepOption,
    type StepDefaults,
  } from './step-list-records'

  const router = useRouter(),
    enumStore = useEnum(),
    pageData = usePageData()
  const conditionItems = createConditionItems()
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product' && item.key !== 'module')
  )
  const filterValue = (key: string): unknown =>
    conditionItems.find((item) => item.key === key)?.value
  const projectProduct = computed(() => stepOptionId(filterValue('project_product'))),
    selectedModule = computed(() => stepOptionId(filterValue('module')))
  const editorRef = ref<{
    open: (row?: StepListRow | null, defaults?: StepDefaults) => void
    close: () => void
  } | null>(null)
  const referencesRef = ref<{ open: (row: StepListRow) => void; close: () => void } | null>(null)
  const rows = ref<StepListRow[]>([]),
    listLoading = ref(false),
    listError = ref(''),
    selectedRowKeys = ref<StepListId[]>([])
  const userOptions = ref<StepOption[]>([]),
    usersLoading = ref(false),
    usersError = ref('')
  const statusOptions = ref<StepOption[]>([]),
    enumsLoading = ref(false),
    enumsError = ref('')
  const pageOptions = ref<StepOption[]>([]),
    pagesLoading = ref(false),
    pagesError = ref('')
  const editingBusy = ref(false),
    deleting = ref(false),
    deletingIds = ref(new Set<string>()),
    actionError = ref(''),
    sidebarResetKey = ref(0)
  const runningId = ref<StepListId | null>(null)
  const pagination = usePagination(() => doRefresh(), listLoading)
  let listSequence = 0,
    usersSequence = 0,
    enumsSequence = 0,
    pagesSequence = 0,
    confirmationVersion = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  function closeConfirmation() {
    confirmationVersion++
    confirmation?.close()
    confirmation = null
  }
  const user = useUserStore(),
    permission = usePermissionStore()
  watch(
    () =>
      JSON.stringify([
        user.userId,
        user.roleId,
        user.token,
        user.selected_environment,
        permission.permissionKeys,
      ]),
    () => {
      conditionItems.forEach((item) => {
        item.value = item.multiple ? [] : null
      })
      pagination.page = 1
      sidebarResetKey.value++
    },
    { flush: 'sync' }
  )
  const polling = usePagePolling(() => doRefresh(false))
  const scope = useLiveWorkbenchScope(() => null, {
    invalidate() {
      listSequence++
      usersSequence++
      enumsSequence++
      pagesSequence++
      polling.stop()
      closeConfirmation()
      editorRef.value?.close()
      referencesRef.value?.close()
      rows.value = []
      selectedRowKeys.value = []
      userOptions.value = []
      statusOptions.value = []
      pageOptions.value = []
      listError.value =
        usersError.value =
        enumsError.value =
        pagesError.value =
        actionError.value =
          ''
      listLoading.value = usersLoading.value = enumsLoading.value = pagesLoading.value = false
      pagination.setTotalSize(0)
    },
    resume: initialize,
  })
  function setFilter(key: string, value: unknown) {
    const item = conditionItems.find((item) => item.key === key)
    if (item) item.value = value
  }
  function clearInteractions() {
    closeConfirmation()
    editorRef.value?.close()
    referencesRef.value?.close()
    selectedRowKeys.value = []
  }
  function onSelectionChange(values: unknown[]) {
    const visible = new Map(rows.value.map((row) => [String(row.id), row.id]))
    selectedRowKeys.value = [
      ...new Set(values.map(stepListId).filter((id): id is StepListId => id !== null)),
    ].flatMap((id) => {
      const value = visible.get(String(id))
      return value === undefined ? [] : [value]
    })
  }
  function onSearch() {
    if (!scope.available()) return
    pagination.page = 1
    clearInteractions()
    return doRefresh()
  }
  function onResetSearch() {
    conditionItems.forEach((item) => {
      item.value = item.multiple ? [] : null
    })
    sidebarResetKey.value++
    void loadPages()
    return onSearch()
  }
  function onSidebarFilterChange(filter: { projectProduct: unknown; module: unknown }) {
    setFilter('project_product', stepOptionId(filter.projectProduct))
    setFilter('module', stepOptionId(filter.module))
    setFilter('page_id', [])
    void loadPages()
    return onSearch()
  }
  async function doRefresh(showLoading = true): Promise<boolean> {
    if (!showLoading && listLoading.value) return false
    const valid = scope.capture(),
      request = ++listSequence
    if (!valid()) return false
    if (showLoading) {
      clearInteractions()
      listLoading.value = true
    }
    listError.value = ''
    try {
      const query = stepListQuery(
        getFormItems(conditionItems),
        pagination.page,
        pagination.pageSize
      )
      const result = readStepList(await getUiSteps(query, !showLoading))
      if (!valid() || request !== listSequence) return false
      const last = Math.max(1, Math.ceil(result.total / pagination.pageSize))
      if (pagination.page > last) {
        pagination.page = last
        return await doRefresh(showLoading)
      }
      rows.value = result.rows
      pagination.setTotalSize(result.total)
      selectedRowKeys.value = selectedRowKeys.value.filter((id) =>
        rows.value.some((row) => String(row.id) === String(id))
      )
      if (rows.value.some(isPendingExecution)) polling.start()
      else polling.stop()
      return true
    } catch (loadFailure0) {
      if (valid() && request === listSequence) (reportLoadError(loadFailure0, "步骤列表加载失败，请重试", false), listError.value = '步骤列表加载失败，请重试')
      return false
    } finally {
      if (valid() && request === listSequence && showLoading) listLoading.value = false
    }
  }
  async function loadUsers() {
    const valid = scope.capture(),
      request = ++usersSequence
    if (!valid()) return
    usersLoading.value = true
    usersError.value = ''
    try {
      const result = readStepOptions(await getUserName())
      if (valid() && request === usersSequence) userOptions.value = result
    } catch (loadFailure1) {
      if (valid() && request === usersSequence) (reportLoadError(loadFailure1, "更新人选项加载失败，请重试", false), usersError.value = '更新人选项加载失败，请重试')
    } finally {
      if (valid() && request === usersSequence) usersLoading.value = false
    }
  }
  async function loadEnums() {
    const valid = scope.capture(),
      request = ++enumsSequence
    if (!valid()) return
    enumsLoading.value = true
    enumsError.value = ''
    try {
      await enumStore.getEnum()
      if (valid() && request === enumsSequence)
        statusOptions.value = enumStore.task_status.map((item) => ({
          key: item.key,
          title: item.title,
        }))
    } catch (loadFailure2) {
      if (valid() && request === enumsSequence) (reportLoadError(loadFailure2, "结果选项加载失败，请重试", false), enumsError.value = '结果选项加载失败，请重试')
    } finally {
      if (valid() && request === enumsSequence) enumsLoading.value = false
    }
  }
  async function loadPages() {
    const valid = scope.capture(),
      request = ++pagesSequence,
      module = selectedModule.value,
      product = projectProduct.value
    if (!valid()) return
    pageOptions.value = []
    pagesError.value = ''
    pagesLoading.value = true
    try {
      const options = readStepOptions(await getUiPageName(module, product ?? undefined))
      if (valid() && request === pagesSequence) pageOptions.value = options
    } catch (loadFailure3) {
      if (valid() && request === pagesSequence) (reportLoadError(loadFailure3, "所属页面加载失败，请重试", false), pagesError.value = '所属页面加载失败，请重试')
    } finally {
      if (valid() && request === pagesSequence) pagesLoading.value = false
    }
  }
  function initialize() {
    if (!scope.available()) return
    void doRefresh()
    void loadUsers()
    void loadEnums()
    void loadPages()
  }
  function onAdd() {
    if (editingBusy.value || deleting.value || !scope.available()) return
    closeConfirmation()
    editorRef.value?.open(null, {
      projectProduct: projectProduct.value,
      module: selectedModule.value,
    })
  }
  function onUpdate(value: unknown) {
    if (editingBusy.value || deleting.value || listLoading.value || !scope.available()) return
    closeConfirmation()
    try {
      editorRef.value?.open(readStepListRow(value))
    } catch (requestFailure) {
      actionError.value = requestFailureMessage(requestFailure, '步骤记录格式不正确，请重新加载')
    }
  }
  function onSaved() {
    void doRefresh()
  }
  function onDelete(value: unknown | null) {
    if (editingBusy.value || deleting.value || listLoading.value || !scope.available()) return
    let ids: StepListId[]
    try {
      ids = value === null ? [...selectedRowKeys.value] : [readStepListRow(value).id]
    } catch (requestFailure) {
      actionError.value = requestFailureMessage(requestFailure, '步骤记录格式不正确')
      return
    }
    if (!ids.length) {
      Message.error('请选择要删除的数据')
      return
    }
    closeConfirmation()
    editorRef.value?.close()
    actionError.value = ''
    const valid = scope.capture(),
      version = confirmationVersion,
      current = () => valid() && version === confirmationVersion
    confirmation = Modal.confirm({
      title: '提示',
      content: '是否要删除此步骤？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: async () => {
        if (!current() || deleting.value || editingBusy.value) return false
        deleting.value = true
        deletingIds.value = new Set(ids.map(String))
        try {
          stepListResponse(await deleteUiSteps(value === null ? [...ids] : ids[0]))
          if (!current()) {
            if (scope.available()) void doRefresh(false)
            return false
          }
          rows.value = rows.value.filter((row) => !ids.some((id) => String(id) === String(row.id)))
          selectedRowKeys.value = selectedRowKeys.value.filter(
            (id) => !ids.some((target) => String(target) === String(id))
          )
          Message.success('删除成功')
          closeConfirmation()
          void doRefresh()
          return true
        } catch (requestFailure) {
          if (current()) actionError.value = requestFailureMessage(requestFailure, '删除失败，请重试')
          return false
        } finally {
          deleting.value = false
          deletingIds.value = new Set()
        }
      },
      onClose: () => {
        if (version === confirmationVersion) {
          confirmationVersion++
          confirmation = null
        }
      },
    })
  }
  async function onRunCase(value: unknown) {
    if (runningId.value !== null || !scope.available()) return
    if (user.selected_environment == null) {
      actionError.value = '请先选择用例执行的环境'
      return
    }
    let row: StepListRow
    try {
      row = readStepListRow(value)
    } catch (requestFailure) {
      actionError.value = requestFailureMessage(requestFailure, '步骤记录格式不正确')
      return
    }
    const valid = scope.capture(),
      id = row.id,
      environment = user.selected_environment
    runningId.value = id
    actionError.value = ''
    try {
      stepListResponse(await getUiStepsTest(id, environment))
      if (valid()) {
        Message.success('调试已提交')
        polling.start()
        void doRefresh(false)
      }
    } catch (requestFailure) {
      if (valid()) actionError.value = requestFailureMessage(requestFailure, '调试请求失败，请先确认执行状态后再重试')
    } finally {
      runningId.value = null
      if (scope.available() && !valid()) void doRefresh(false)
    }
  }
  function onReferences(value: unknown) {
    if (!scope.available()) return
    try {
      referencesRef.value?.open(readStepListRow(value))
    } catch (requestFailure) {
      actionError.value = requestFailureMessage(requestFailure, '步骤记录格式不正确')
    }
  }
  function onSteps(value: unknown) {
    if (!scope.available()) return
    try {
      const row = readStepListRow(value)
      pageData.setRecord(row)
      const valid = scope.capture()
      void router
        .push({ path: '/uitest/page/steps/details', query: { id: String(row.id) } })
        .catch(() => {
          if (valid()) actionError.value = '打开步骤配置失败，请重试'
        })
    } catch (requestFailure) {
      actionError.value = requestFailureMessage(requestFailure, '步骤记录格式不正确，请重新加载')
    }
  }
  onMounted(initialize)
</script>
<style scoped>
  .mango-ui-step-list-body {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-height: 0;
    min-width: 0;
    height: 100%;
  }
  .mango-ui-step-list-table {
    flex: 1;
    min-height: 0;
    min-width: 0;
  }
</style>
