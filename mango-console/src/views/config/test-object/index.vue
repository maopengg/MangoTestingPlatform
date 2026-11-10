<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="测试对象" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="selectedProduct"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
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
              <template v-else-if="item.type === 'select' && item.key === 'environment'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="enumStore.environment_type"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'auto_type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="enumStore.auto_type"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="item.optionItems"
                  :loading="usersLoading"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearch"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-button
              type="primary"
              size="small"
              :disabled="editorSaving"
              @click="onAdd"
              data-testid="qa-views-config-test-object-button-新增"
              >新增</a-button
            >
          </a-space>
        </template>


        <a-table
          class="mango-native-scroll-table"
          :scroll="{ x: tableScrollX, y: '100%' }"
          :bordered="false"
          :loading="listLoading"
          :data="rows"
          :columns="tableColumns"
          :pagination="false"
          row-key="id"
        >
          <template #columns>
            <a-table-column
              v-for="item of tableColumns"
              :key="item.key"
              :align="item.align"
              :title="item.title"
              :width="item.width"
              :data-index="item.key"
              :fixed="item.fixed"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'auto_type'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.auto_type]" size="small"
                  >{{
                    enumStore.auto_type.find(
                      (item) => String(item.key) === String(record.auto_type)
                    )?.title || '-'
                  }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'value'" #cell="{ record }">
                <TestTargetDisplay :value="record.value" :config="record.target_config" />
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                {{ record.update_user?.name || record.update_user?.username || '-' }}
              </template>
              <template v-else-if="item.key === 'environment'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.environment]" size="small">
                  {{
                    enumStore.environment_type.find(
                      (item) => String(item.key) === String(record.environment)
                    )?.title || '-'
                  }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    {
                      label: '测试',
                      hidden: !record.network_test_addresses?.length,
                      loading: testingIds.has(record.id),
                      disabled: editorSaving || isWriting(record.id),
                      onClick: () => onTest(record),
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
                      disabled: testingIds.has(record.id) || editingIds.has(record.id),
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
  <TestObjectEditor ref="editorRef" @saved="doRefresh" @saving-change="onEditorSaving" />
  <TestConnectionDialog ref="connectionDialog" @testing-change="onTestingChange" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, reactive, ref } from 'vue'
  import { usePagination } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import { deleteUserTestObject, getUserTestObject } from '@/api/system/test_object'
  import { getUserName } from '@/api/user/user'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { setUpdateUserOptions } from '@/utils/update-user'
  import { formatProjectProductPath } from '@/utils/business-format'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import TestObjectEditor from './components/TestObjectEditor.vue'
  import TestConnectionDialog from './components/TestConnectionDialog.vue'
  import TestTargetDisplay from './components/TestTargetDisplay.vue'
  import { tableColumns, createConditionItems, tableScrollX } from './config'
  import { productId } from './form'
  import { useTestObjectScope } from './composables/useTestObjectScope'
  import type { TestObjectRecord, TestObjectEditorHandle, ConnectionDialogHandle } from './types'
  const enumStore = useEnum()
  const conditionItems = createConditionItems()
  const projectProductCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const selectedProduct = computed(() => productId(projectProductCondition.value?.value))
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product')
  )
  const rows = ref<TestObjectRecord[]>([]),
    listLoading = ref(false),
    loadError = ref('')
  const usersLoading = ref(false),
    usersError = ref(false)
  const pagination = usePagination(doRefresh, listLoading)
  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const editorRef = ref<TestObjectEditorHandle | null>(null),
    connectionDialog = ref<ConnectionDialogHandle | null>(null)
  const editorSaving = ref(false),
    sidebarResetKey = ref(0)
  const editingIds = reactive(new Set<number>()),
    deletingIds = reactive(new Set<number>()),
    testingIds = reactive(new Set<number>())
  let listRequest = 0,
    usersRequest = 0,
    context = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useTestObjectScope(reset, () => {
    void doRefresh()
    void loadUsers()
  })
  const isWriting = (id: number) => editingIds.has(id) || deletingIds.has(id)
  const isBusy = (id: number) => isWriting(id) || testingIds.has(id)
  function closeOperations() {
    ++context
    editorRef.value?.close()
    connectionDialog.value?.close()
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
    Object.assign(payload, { page: pagination.page, pageSize: pagination.pageSize })
    listLoading.value = true
    loadError.value = ''
    try {
      const response = await getUserTestObject(payload)
      if (request !== listRequest || !scope.current(version)) return
      rows.value = response.data || []
      pagination.setTotalSize(response.totalSize ?? 0)
    } catch (loadFailure1) {
      if (request === listRequest && scope.current(version))
        void (reportLoadError(loadFailure1, "测试对象加载失败，请重试", false), loadError.value = '测试对象加载失败，请重试')
    } finally {
      if (request === listRequest) listLoading.value = false
    }
  }
  function onSearch() {
    pagination.page = 1
    return doRefresh()
  }
  function onSidebarFilterChange({ projectProduct }: { projectProduct: string | number | null }) {
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
  function onEditorSaving(id: number | null, pending: boolean) {
    editorSaving.value = pending
    if (id !== null) {
      if (pending) editingIds.add(id)
      else editingIds.delete(id)
    }
  }
  function onUpdate(record: TestObjectRecord) {
    if (!scope.isActive() || editorSaving.value || isBusy(record.id)) return
    connectionDialog.value?.close()
    editorRef.value?.open(record)
  }
  function onAdd() {
    if (!scope.isActive() || editorSaving.value) return
    connectionDialog.value?.close()
    editorRef.value?.open(
      undefined,
      navigationCreateRef.value?.getCreateDefaults().projectProduct ?? null
    )
  }
  function onTestingChange(id: number, pending: boolean) {
    if (pending) testingIds.add(id)
    else testingIds.delete(id)
  }
  function onTest(record: TestObjectRecord) {
    if (
      !scope.isActive() ||
      editorSaving.value ||
      isBusy(record.id) ||
      !record.network_test_addresses?.length
    )
      return
    editorRef.value?.close()
    connectionDialog.value?.open(record)
  }
  function onDelete(record: TestObjectRecord) {
    if (!scope.isActive() || confirmation || isBusy(record.id)) return
    const id = record.id,
      version = scope.snapshot(),
      current = context
    const dialog = Modal.confirm({
      title: '提示',
      content: '是否要删除此测试环境？',
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!scope.current(version) || current !== context || isBusy(id)) return false
        deletingIds.add(id)
        try {
          const response = await deleteUserTestObject(id)
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
  onMounted(() => {
    void doRefresh()
    void loadUsers()
  })
</script>
