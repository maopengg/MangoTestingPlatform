<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header><TableHeader title="页面元素" /></template>
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
                v-else-if="item.key === 'project_product__ui_client_type'"
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="clientOptions"
                :loading="enumsLoading"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                value-key="key"
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
              data-testid="qa-views-uitest-page-button-新增"
              @click="onAdd"
              >新增</a-button
            >
            <a-button
              status="danger"
              size="small"
              :loading="deleting"
              :disabled="editingBusy || !selectedRowKeys.length"
              data-testid="qa-views-uitest-page-button-批量删除"
              @click="onDelete(null)"
              >批量删除</a-button
            >
          </a-space>
        </template>
        <div class="mango-ui-page-body">
          
          
          
          <a-alert v-if="actionError" type="error" closable @close="actionError = ''">{{
            actionError
          }}</a-alert>
          <a-table
            class="mango-native-scroll-table mango-ui-page-table"
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
                <template v-else-if="item.key === 'client'" #cell="{ record }"
                  ><a-tag
                    :color="enumStore.colors[record.project_product?.ui_client_type]"
                    size="small"
                    >{{ clientTitle(record) }}</a-tag
                  ></template
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
                        label: '编辑',
                        disabled: editingBusy || deleting || listLoading,
                        onClick: () => onUpdate(record),
                      },
                      { label: '添加元素', disabled: listLoading, onClick: () => onElements(record) },
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
  <UiPageEditor ref="editorRef" @saved="onSaved" @busy-change="editingBusy = $event" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, ref, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { getUiPage, deleteUiPage } from '@/api/uitest/page'
  import { getUserName } from '@/api/user/user'
  import { usePagination } from '@/hooks/table'
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
  import UiPageEditor from './components/UiPageEditor.vue'
  import { createConditionItems, tableColumns, TABLE_SCROLL_X } from './config'
  import {
    pageId,
    pageOptionId,
    pageQuery,
    pageResponse,
    readPageList,
    readPageUsers,
    readUiPage,
    type UiPageRow,
    type PageId,
    type PageUserOption,
    type PageDefaults,
  } from './page-records'

  const router = useRouter(),
    enumStore = useEnum(),
    pageData = usePageData()
  const conditionItems = createConditionItems()
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product' && item.key !== 'module')
  )
  const filterValue = (key: string): unknown =>
    conditionItems.find((item) => item.key === key)?.value
  const projectProduct = computed(() => pageOptionId(filterValue('project_product'))),
    selectedModule = computed(() => pageOptionId(filterValue('module')))
  const editorRef = ref<{
    open: (row?: UiPageRow | null, defaults?: PageDefaults) => void
    close: () => void
  } | null>(null)
  const rows = ref<UiPageRow[]>([]),
    listLoading = ref(false),
    listError = ref(''),
    selectedRowKeys = ref<PageId[]>([])
  const userOptions = ref<PageUserOption[]>([]),
    usersLoading = ref(false),
    usersError = ref('')
  const clientOptions = ref<PageUserOption[]>([]),
    enumsLoading = ref(false),
    enumsError = ref('')
  const editingBusy = ref(false),
    deleting = ref(false),
    deletingIds = ref(new Set<string>()),
    actionError = ref(''),
    sidebarResetKey = ref(0)
  const pagination = usePagination(doRefresh, listLoading)
  let listSequence = 0,
    usersSequence = 0,
    enumsSequence = 0,
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
  const scope = useLiveWorkbenchScope(() => null, {
    invalidate() {
      listSequence++
      usersSequence++
      enumsSequence++
      closeConfirmation()
      editorRef.value?.close()
      rows.value = []
      userOptions.value = []
      clientOptions.value = []
      selectedRowKeys.value = []
      listError.value = usersError.value = enumsError.value = actionError.value = ''
      listLoading.value = usersLoading.value = enumsLoading.value = false
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
    selectedRowKeys.value = []
  }
  function onSelectionChange(values: unknown[]) {
    const visible = new Map(rows.value.map((row) => [String(row.id), row.id]))
    selectedRowKeys.value = [
      ...new Set(values.map(pageId).filter((id): id is PageId => id !== null)),
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
    return onSearch()
  }
  function onSidebarFilterChange(filter: { projectProduct: unknown; module: unknown }) {
    setFilter('project_product', pageOptionId(filter.projectProduct))
    setFilter('module', pageOptionId(filter.module))
    return onSearch()
  }
  async function doRefresh(): Promise<boolean> {
    const valid = scope.capture(),
      request = ++listSequence
    if (!valid()) {
      listLoading.value = false
      return false
    }
    clearInteractions()
    listLoading.value = true
    listError.value = ''
    try {
      const query = pageQuery(getFormItems(conditionItems), pagination.page, pagination.pageSize)
      const response: unknown = await getUiPage(query)
      if (!valid() || request !== listSequence) return false
      const result = readPageList(response),
        last = Math.max(1, Math.ceil(result.total / query.pageSize))
      if (query.page > last) {
        pagination.page = last
        return await doRefresh()
      }
      rows.value = result.rows
      pagination.setTotalSize(result.total)
      return true
    } catch (loadFailure0) {
      if (valid() && request === listSequence) (reportLoadError(loadFailure0, "页面列表加载失败，请重试", false), listError.value = '页面列表加载失败，请重试')
      return false
    } finally {
      if (valid() && request === listSequence) listLoading.value = false
    }
  }
  async function loadUsers() {
    const valid = scope.capture(),
      request = ++usersSequence
    if (!valid()) return
    usersLoading.value = true
    usersError.value = ''
    try {
      const result = readPageUsers(await getUserName())
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
        clientOptions.value = enumStore.drive_type.map((item) => ({
          key: item.key,
          title: item.title,
        }))
    } catch (loadFailure2) {
      if (valid() && request === enumsSequence) (reportLoadError(loadFailure2, "端类型选项加载失败，请重试", false), enumsError.value = '端类型选项加载失败，请重试')
    } finally {
      if (valid() && request === enumsSequence) enumsLoading.value = false
    }
  }
  function clientTitle(row: UiPageRow) {
    return (
      clientOptions.value.find(
        (item) => String(item.key) === String(row.project_product?.ui_client_type)
      )?.title || '-'
    )
  }
  function initialize() {
    void doRefresh()
    void loadUsers()
    void loadEnums()
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
      editorRef.value?.open(readUiPage(value))
    } catch {
      actionError.value = '页面记录格式不正确，请重新加载'
    }
  }
  function onSaved() {
    void doRefresh()
  }
  function onDelete(value: unknown | null) {
    if (editingBusy.value || deleting.value || listLoading.value || !scope.available()) return
    let ids: PageId[]
    try {
      ids = value === null ? [...selectedRowKeys.value] : [readUiPage(value).id]
    } catch {
      actionError.value = '页面记录格式不正确'
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
      content: '是否要删除此页面？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: async () => {
        if (!current() || deleting.value || editingBusy.value) return false
        deleting.value = true
        deletingIds.value = new Set(ids.map(String))
        try {
          pageResponse(await deleteUiPage(value === null ? [...ids] : ids[0]))
          if (!current()) return false
          // 写入已接受，后续列表读取失败时只重试读取。
          rows.value = rows.value.filter((row) => !ids.some((id) => String(id) === String(row.id)))
          selectedRowKeys.value = selectedRowKeys.value.filter(
            (id) => !ids.some((target) => String(target) === String(id))
          )
          Message.success('删除成功')
          closeConfirmation()
          void doRefresh()
          return true
        } catch {
          if (current()) actionError.value = '删除失败，请重试'
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
  function onElements(value: unknown) {
    if (!scope.available()) return
    try {
      const row = readUiPage(value)
      pageData.setRecord(row)
      const valid = scope.capture()
      void router.push({ path: '/uitest/page/elements', query: { id: String(row.id) } }).catch(() => {
        if (valid()) actionError.value = '打开元素配置失败，请重试'
      })
    } catch {
      actionError.value = '页面记录格式不正确，请重新加载'
    }
  }
  onMounted(initialize)
</script>
<style scoped>
  .mango-ui-page-body {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-height: 0;
    min-width: 0;
    height: 100%;
  }
  .mango-ui-page-table {
    flex: 1;
    min-height: 0;
    min-width: 0;
  }
</style>
