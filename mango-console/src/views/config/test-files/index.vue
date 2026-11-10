<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="测试文件" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="selectedProduct"
        :reset-key="sidebarResetKey"
        @filter-change="onNavigationFilterChange"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form layout="inline" :model="{}" @keyup.enter="onSearch">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearch"
                  @clear="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="item.optionItems"
                  :loading="usersLoading"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="onSearch"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-button
              size="small"
              type="primary"
              :disabled="uploadPending"
              @click="onOpenUploadModal"
              data-testid="qa-views-config-test-files-button-上传"
              >上传</a-button
            >
          </a-space>
        </template>
        
        
        <a-table
          :scroll="{ x: tableScrollX, y: '100%' }"
          class="mango-test-files-table mango-native-scroll-table"
          :bordered="false"
          :columns="visibleTableColumns"
          :data="rows"
          :loading="listLoading"
          :pagination="false"
          row-key="id"
        >
          <template #columns>
            <a-table-column
              v-for="item of visibleTableColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.key"
              :ellipsis="item.ellipsis"
              :fixed="item.fixed"
              :title="item.title"
              :tooltip="item.tooltip"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'file_size'" #cell="{ record }">
                {{ record.file_size_display || formatFileSize(record.file_size) }}
              </template>
              <template v-else-if="item.key === 'allow_download'" #cell="{ record }">
                <a-tag :color="isAllowDownload(record) ? 'green' : 'orange'" size="small">
                  {{ isAllowDownload(record) ? '允许下载' : '限制下载' }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                {{ record.update_user?.name || record.update_user?.username || '-' }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    {
                      label: '下载',
                      loading: downloadingIds.has(record.id),
                      disabled: isWriting(record.id),
                      onClick: () => onDownload(record),
                    },
                    {
                      label: '编辑',
                      disabled: editorSaving || isBusy(record.id),
                      onClick: () => onUpdate(record),
                    },
                    {
                      label: '删除',
                      danger: true,
                      loading: deletingIds.has(record.id),
                      disabled: downloadingIds.has(record.id) || editingIds.has(record.id),
                      onClick: () => onDelete(record),
                    },
                  ]"
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
  <TestFileEditor ref="editorRef" @saved="doRefresh" @saving-change="onEditorSaving" />
  <TestFileUploadDialog
    ref="uploadRef"
    @saved="doRefresh"
    @uploading-change="uploadPending = $event"
  />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, reactive, ref } from 'vue'
  import { usePagination } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import { deleteUserFile, getUserFile, getUserFileDownloadUrl } from '@/api/system/file_data'
  import { getUserName } from '@/api/user/user'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { setUpdateUserOptions } from '@/utils/update-user'
  import { formatProjectProductPath } from '@/utils/business-format'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import TestFileEditor from './components/TestFileEditor.vue'
  import TestFileUploadDialog from './components/TestFileUploadDialog.vue'
  import { tableColumns, createConditionItems, tableScrollX } from './config'
  import { formatFileSize, isAllowDownload, productId } from './file'
  import { useTestFileScope } from './composables/useTestFileScope'
  import type { TestFileRecord, TestFileEditorHandle, TestFileUploadHandle } from './types'

  const conditionItems = createConditionItems()
  const projectProductCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const selectedProduct = computed(() => productId(projectProductCondition.value?.value))
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product')
  )
  const visibleTableColumns = tableColumns
  const rows = ref<TestFileRecord[]>([]),
    listLoading = ref(false),
    loadError = ref('')
  const usersLoading = ref(false),
    usersError = ref(false)
  const pagination = usePagination(doRefresh, listLoading)
  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const editorRef = ref<TestFileEditorHandle | null>(null),
    uploadRef = ref<TestFileUploadHandle | null>(null)
  const editorSaving = ref(false),
    uploadPending = ref(false),
    sidebarResetKey = ref(0)
  const editingIds = reactive(new Set<number>()),
    deletingIds = reactive(new Set<number>()),
    downloadingIds = reactive(new Set<number>())
  let listRequest = 0,
    usersRequest = 0,
    context = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useTestFileScope(reset, () => {
    void doRefresh()
    void loadUsers()
  })
  const isWriting = (id: number) => editingIds.has(id) || deletingIds.has(id)
  const isBusy = (id: number) => isWriting(id) || downloadingIds.has(id)
  function closeOperations() {
    ++context
    editorRef.value?.close()
    uploadRef.value?.close()
    confirmation?.close()
    confirmation = null
  }
  function reset() {
    ++listRequest
    ++usersRequest
    closeOperations()
    rows.value = []
    pagination.setTotalSize(0)
    listLoading.value = false
    usersLoading.value = false
    loadError.value = ''
    usersError.value = false
    setUpdateUserOptions(conditionItems, [])
  }
  async function loadUsers() {
    if (!scope.isActive()) return
    const request = ++usersRequest,
      version = scope.snapshot()
    usersLoading.value = true
    usersError.value = false
    try {
      const response = await getUserName()
      if (request === usersRequest && scope.current(version))
        setUpdateUserOptions(conditionItems, response.data || [])
    } catch (loadFailure0) {
      if (request === usersRequest && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), usersError.value = true)
    } finally {
      if (request === usersRequest) usersLoading.value = false
    }
  }
  async function doRefresh() {
    if (!scope.isActive()) return
    const request = ++listRequest,
      version = scope.snapshot()
    const payload = getFormItems(conditionItems)
    payload.project_product = selectedProduct.value
    Object.keys(payload).forEach((key) => {
      if (payload[key] === '' || payload[key] === null || payload[key] === undefined)
        delete payload[key]
    })
    Object.assign(payload, { page: pagination.page, pageSize: pagination.pageSize, type: 0 })
    listLoading.value = true
    loadError.value = ''
    try {
      const response = await getUserFile(payload)
      if (request !== listRequest || !scope.current(version)) return
      rows.value = response.data || []
      pagination.setTotalSize(response.totalSize ?? 0)
    } catch (loadFailure1) {
      if (request === listRequest && scope.current(version))
        void (reportLoadError(loadFailure1, "测试文件加载失败，请重试", false), loadError.value = '测试文件加载失败，请重试')
    } finally {
      if (request === listRequest) listLoading.value = false
    }
  }
  function onSearch() {
    pagination.page = 1
    return doRefresh()
  }
  function onNavigationFilterChange({
    projectProduct,
  }: {
    projectProduct: string | number | null
  }) {
    closeOperations()
    if (projectProductCondition.value) projectProductCondition.value.value = projectProduct ?? ''
    return onSearch()
  }
  function onResetSearch() {
    closeOperations()
    conditionItems.forEach((item) => {
      item.value = item.multiple ? [] : ''
    })
    sidebarResetKey.value++
    return onSearch()
  }
  function onEditorSaving(id: number, pending: boolean) {
    editorSaving.value = pending
    if (pending) editingIds.add(id)
    else editingIds.delete(id)
  }
  function onUpdate(record: TestFileRecord) {
    if (scope.isActive() && !editorSaving.value && !isBusy(record.id)) editorRef.value?.open(record)
  }
  function onOpenUploadModal() {
    if (scope.isActive() && !uploadPending.value)
      uploadRef.value?.open(navigationCreateRef.value?.getCreateDefaults().projectProduct ?? null)
  }
  function onDelete(record: TestFileRecord) {
    if (!scope.isActive() || confirmation || isBusy(record.id)) return
    const id = record.id,
      version = scope.snapshot(),
      current = context
    const dialog = Modal.confirm({
      title: '提示',
      content: '是否要删除此数据？',
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!scope.current(version) || current !== context || isBusy(id)) return false
        deletingIds.add(id)
        try {
          const response = await deleteUserFile(id)
          if (scope.current(version) && current === context) {
            Message.success(response.msg)
            if (rows.value.length === 1 && rows.value[0].id === id && pagination.page > 1)
              pagination.page--
            await doRefresh()
          }
          return true
        } catch {
          return false
        } finally {
          deletingIds.delete(id)
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  async function onDownload(record: TestFileRecord) {
    if (!scope.isActive() || isBusy(record.id)) return
    const id = record.id,
      name = record.name,
      version = scope.snapshot(),
      current = context
    downloadingIds.add(id)
    try {
      const response = await getUserFileDownloadUrl(id)
      if (!scope.current(version) || current !== context) return
      if (name.includes('jpg') || name.includes('png')) window.open(response.data, '_blank')
      else {
        const link = document.createElement('a')
        link.href = response.data
        link.download = name
        document.body.appendChild(link)
        try {
          link.click()
        } finally {
          link.remove()
        }
      }
    } catch {
      /* 请求层统一展示后端错误，保留重试入口。 */
    } finally {
      downloadingIds.delete(id)
    }
  }
  onMounted(() => {
    void doRefresh()
    void loadUsers()
  })
</script>
<style scoped>
  .mango-test-files-table {
    width: 100%;
  }
</style>
