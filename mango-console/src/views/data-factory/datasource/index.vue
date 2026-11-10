<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header><TableHeader title="数据工厂 / 数据库映射" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationRef"
        contained-body
        :model-value="selectedProduct"
        :reset-key="sidebarResetKey"
        @filter-change="onFilterChange"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <a-input
                v-if="item.type === 'input'"
                v-model="item.value"
                :placeholder="item.placeholder"
                allow-clear
                @blur="onSearch"
                @clear="onSearch"
              />
              <a-select
                v-else-if="item.type === 'select'"
                v-model="item.value"
                :multiple="item.multiple"
                :max-tag-count="item.multiple ? 1 : undefined"
                :field-names="enumFieldNames"
                :options="item.key === 'db_type' ? enumStore.data_source_type : item.optionItems"
                :loading="item.key === 'db_type' ? enumsLoading : usersLoading"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                @change="onSearch"
              />
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-button
            size="small"
            type="primary"
            :disabled="aliasSaving"
            @click="openAlias()"
            data-testid="qa-views-data-factory-datasource-button-新增逻辑源"
            >新增逻辑源</a-button
          >
        </template>



        <a-table
          class="mango-native-scroll-table"
          :scroll="{ x: aliasScrollX, y: '100%' }"
          :columns="datasourceAliasColumns"
          :data="rows"
          :loading="listLoading"
          :pagination="false"
          :bordered="false"
          row-key="id"
        >
          <template #columns>
            <a-table-column
              v-for="item of datasourceAliasColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.key"
              :fixed="item.fixed"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
              :title="item.title"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">{{
                formatProjectProductPath(record.project_product)
              }}</template>
              <template v-else-if="item.key === 'db_type'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.db_type]" size="small">{{
                  enumStore.data_source_type.find(
                    (item) => String(item.key) === String(record.db_type)
                  )?.title ?? record.db_type
                }}</a-tag>
              </template>
              <template v-else-if="item.key === 'update_user'" #cell="{ record }">{{
                record.update_user?.name || record.update_user?.username || '-'
              }}</template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    {
                      label: '编辑',
                      disabled: aliasSaving || isBusy(record.id),
                      onClick: () => openAlias(record),
                    },
                    {
                      label: '环境绑定',
                      disabled: aliasSaving || isBusy(record.id),
                      onClick: () => openBinding(record),
                    },
                    {
                      label: '删除',
                      danger: true,
                      loading: deletingIds.has(record.id),
                      disabled: aliasSaving || bindingWritingIds.size > 0,
                      onClick: () => removeAlias(record),
                    },
                  ]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <DatasourceAliasEditor
    ref="editorRef"
    :options-loading="enumsLoading"
    @saved="doRefresh"
    @saving-change="onAliasSaving"
  />
  <DatasourceBindingsDrawer ref="bindingsRef" @writing-change="onBindingWriting" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination } from '@/hooks/table'
  import {
    getDataFactoryDatasourceAlias,
    deleteDataFactoryDatasourceAlias,
  } from '@/api/data-factory'
  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { getFormItems } from '@/utils/datacleaning'
  import { formatProjectProductPath } from '@/utils/business-format'
  import { setUpdateUserOptions } from '@/utils/update-user'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import DatasourceAliasEditor from './components/DatasourceAliasEditor.vue'
  import DatasourceBindingsDrawer from './components/DatasourceBindingsDrawer.vue'
  import {
    createConditionItems,
    datasourceAliasColumns,
    aliasScrollX,
    enumFieldNames,
  } from './config'
  import { productId } from './form'
  import { useDatasourceScope } from './composables/useDatasourceScope'
  import type { LogicalSource, AliasEditorHandle, BindingsDrawerHandle } from './types'
  const enumStore = useEnum()
  const conditionItems = createConditionItems()
  const productCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const selectedProduct = computed(() => productId(productCondition.value?.value))
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product')
  )
  const rows = ref<LogicalSource[]>([]),
    listLoading = ref(false),
    loadError = ref(false)
  const enumsLoading = ref(false),
    enumsError = ref(false),
    usersLoading = ref(false),
    usersError = ref(false)
  const pagination = usePagination(doRefresh, listLoading)
  const navigationRef = ref<NavigationCreateSource | null>(null)
  const editorRef = ref<AliasEditorHandle | null>(null),
    bindingsRef = ref<BindingsDrawerHandle | null>(null)
  const aliasSaving = ref(false),
    sidebarResetKey = ref(0)
  const deletingIds = reactive(new Set<number>()),
    editingIds = reactive(new Set<number>()),
    bindingWritingIds = reactive(new Set<number>())
  let listRequest = 0,
    enumsRequest = 0,
    usersRequest = 0,
    context = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useDatasourceScope(reset, resume)
  const isBusy = (id: number) =>
    deletingIds.has(id) || editingIds.has(id) || bindingWritingIds.has(id)
  function closeOperations() {
    ++context
    editorRef.value?.close()
    bindingsRef.value?.close()
    confirmation?.close()
    confirmation = null
  }
  function reset() {
    ++listRequest
    ++enumsRequest
    ++usersRequest
    closeOperations()
    rows.value = []
    pagination.setTotalSize(0)
    listLoading.value = false
    loadError.value = false
    enumsLoading.value = false
    enumsError.value = false
    usersLoading.value = false
    usersError.value = false
    setUpdateUserOptions(conditionItems, [])
  }
  function resume() {
    void doRefresh()
    void loadEnums()
    void loadUsers()
  }
  async function loadEnums() {
    if (!scope.isActive()) return
    const request = ++enumsRequest,
      version = scope.snapshot()
    enumsLoading.value = true
    enumsError.value = false
    try {
      await enumStore.getEnum()
    } catch (loadFailure0) {
      if (request === enumsRequest && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), enumsError.value = true)
    } finally {
      if (request === enumsRequest) enumsLoading.value = false
    }
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
    } catch (loadFailure1) {
      if (request === usersRequest && scope.current(version)) (reportLoadError(loadFailure1, "加载失败，请重试", false), usersError.value = true)
    } finally {
      if (request === usersRequest) usersLoading.value = false
    }
  }
  async function doRefresh() {
    if (!scope.isActive()) return
    const request = ++listRequest,
      version = scope.snapshot(),
      payload = getFormItems(conditionItems)
    payload.project_product = selectedProduct.value
    Object.keys(payload).forEach((key) => {
      if (payload[key] === '' || payload[key] === null || payload[key] === undefined)
        delete payload[key]
    })
    Object.assign(payload, { page: pagination.page, pageSize: pagination.pageSize })
    listLoading.value = true
    loadError.value = false
    try {
      const response = await getDataFactoryDatasourceAlias(payload)
      if (request === listRequest && scope.current(version)) {
        rows.value = response.data || []
        pagination.setTotalSize(response.totalSize ?? 0)
      }
    } catch (loadFailure2) {
      if (request === listRequest && scope.current(version)) (reportLoadError(loadFailure2, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (request === listRequest) listLoading.value = false
    }
  }
  function onSearch() {
    pagination.page = 1
    return doRefresh()
  }
  function onFilterChange({ projectProduct }: { projectProduct: string | number | null }) {
    closeOperations()
    if (productCondition.value) productCondition.value.value = projectProduct ?? ''
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
  function onAliasSaving(id: number | null, pending: boolean) {
    aliasSaving.value = pending
    if (id !== null) {
      if (pending) editingIds.add(id)
      else editingIds.delete(id)
    }
  }
  function onBindingWriting(id: number, pending: boolean) {
    if (pending) bindingWritingIds.add(id)
    else bindingWritingIds.delete(id)
  }
  function openAlias(record?: LogicalSource) {
    if (!scope.isActive() || aliasSaving.value || (record && isBusy(record.id))) return
    bindingsRef.value?.close()
    editorRef.value?.open(record, navigationRef.value?.getCreateDefaults().projectProduct ?? null)
  }
  function openBinding(record: LogicalSource) {
    if (!scope.isActive() || aliasSaving.value || isBusy(record.id)) return
    editorRef.value?.close()
    bindingsRef.value?.open(record)
  }
  function removeAlias(record: LogicalSource) {
    if (
      !scope.isActive() ||
      confirmation ||
      aliasSaving.value ||
      bindingWritingIds.size > 0 ||
      isBusy(record.id)
    )
      return
    bindingsRef.value?.close()
    editorRef.value?.close()
    const id = record.id,
      name = record.name,
      version = scope.snapshot(),
      current = context
    const dialog = Modal.confirm({
      title: '删除逻辑源',
      content: `确认删除 ${name}？`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!scope.current(version) || current !== context || isBusy(id)) return false
        deletingIds.add(id)
        try {
          const response = await deleteDataFactoryDatasourceAlias(id)
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
  onMounted(resume)
</script>
