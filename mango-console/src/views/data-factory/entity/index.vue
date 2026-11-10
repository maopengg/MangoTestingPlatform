<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header>
      <TableHeader title="数据工厂 / 数据实体" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :sticky-horizontal-scroll="false"
        :model-value="getSearchItemValue('project_product')"
        :module-value="getSearchItemValue('module')"
        :reset-key="sidebarResetKey"
        show-modules
        @filter-change="onNavigationFilterChange"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearch">
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
              <template v-else-if="item.type === 'select' && item.key === 'datasource_alias'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="{ value: 'id', label: 'name' }"
                  :options="datasourceAliasOptions"
                  :loading="aliasLoading"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="enumFieldNames"
                  :options="statusOptions"
                  :loading="enumsLoading"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="enumFieldNames"
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
          <div>
            <a-space>
              <a-button
                size="small"
                type="primary"
                @click="openEntity()"
                data-testid="qa-views-data-factory-entity-button-新增实体"
                >新增实体</a-button
              >
              <a-button
                size="small"
                @click="openBatchGenerate"
                data-testid="qa-views-data-factory-entity-button-批量生成"
                >批量生成</a-button
              >
            </a-space></div
          >
        </template>


        <a-table
          class="mango-native-scroll-table"
          :columns="visibleTableColumns"
          :data="rows"
          :loading="listLoading"
          :pagination="false"
          :row-key="'id'"
          :scroll="{ x: entityScrollX, y: '100%' }"
        >
          <template #columns>
            <a-table-column
              v-for="item of visibleTableColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.key"
              :fixed="item.fixed"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
              :title="item.title"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'datasource_alias'" #cell="{ record }">
                {{ record?.datasource_alias?.name || '-' }}
              </template>
              <template v-else-if="item.key === 'create_type'" #cell="{ record }">
                <a-tag color="arcoblue" size="small">
                  {{ enumTitle(enumStore.data_factory_operation_type, record.create_type || 2) }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'delete_type'" #cell="{ record }">
                <a-tag color="arcoblue" size="small">SQL</a-tag>
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-tooltip :content="entityStatusTooltip(record)">
                  <a-switch
                    :beforeChange="(newValue) => switchEntityStatus(newValue, record.id)"
                    :model-value="record.status === 1"
                    :loading="statusIds.has(record.id)"
                    :disabled="entitySaving || isBusy(record.id)"
                  />
                </a-tooltip>
              </template>
              <template v-else-if="item.key === 'status_change_source'" #cell="{ record }">
                <a-tooltip :content="entityStatusTooltip(record)">
                  <a-tag :color="statusSourceColor(record.status_change_source)" size="small">
                    {{ statusSourceTitle(record.status_change_source) }}
                  </a-tag>
                </a-tooltip>
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'module'" #cell="{ record }">
                {{ formatModulePath(record.module) }}
              </template>
              <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                {{ record.update_user?.name || record.update_user?.username || '-' }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    {
                      label: '编辑',
                      disabled: entitySaving || isBusy(record.id),
                      onClick: () => openEntity(record),
                    },
                    {
                      label: '字段规则',
                      disabled: entitySaving || isBusy(record.id),
                      onClick: () => openFields(record),
                    },
                    {
                      label: '状态记录',

                      onClick: () => openStatusLogs(record),
                    },
                    {
                      label: '删除',
                      danger: true,
                      loading: deletingIds.has(record.id),
                      disabled:
                        entitySaving || writingIds.has(record.id) || statusIds.has(record.id),
                      onClick: () => removeEntity(record),
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

  <EntityEditor ref="editorRef" @saved="doRefresh" @saving-change="onEntitySaving" />
  <EntityBatchDrawer ref="batchRef" @saved="doRefresh" />
  <EntityFieldsEditor ref="fieldsRef" @saving-change="onFieldSaving" />
  <EntityStatusLogs ref="logsRef" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    getDataFactoryEntity,
    deleteDataFactoryEntity,
    putDataFactoryEntityStatus,
  } from '@/api/data-factory'
  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination } from '@/hooks/table'
  import { getFormItems } from '@/utils/datacleaning'
  import { formatProjectProductPath, formatModulePath } from '@/utils/business-format'
  import { setUpdateUserOptions } from '@/utils/update-user'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import EntityEditor from './components/EntityEditor.vue'
  import EntityBatchDrawer from './components/EntityBatchDrawer.vue'
  import EntityFieldsEditor from './components/EntityFieldsEditor.vue'
  import EntityStatusLogs from './components/EntityStatusLogs.vue'
  import {
    createConditionItems,
    entityTableColumns,
    entityScrollX,
    enumFieldNames,
    statusOptions,
  } from './config'
  import { enumTitle, statusSourceColor, statusTooltip } from './display'
  import { optionId } from './form'
  import { useEntityScope } from './composables/useEntityScope'
  import { useEntityAliases } from './composables/useEntityAliases'
  import type {
    EntityRecord,
    EntityEditorHandle,
    BatchPanelHandle,
    RecordPanelHandle,
  } from './types'
  const enumStore = useEnum(),
    aliases = useEntityAliases()
  const { options: datasourceAliasOptions, loading: aliasLoading, error: aliasError } = aliases
  const navigationCreateRef = ref<NavigationCreateSource | null>(null),
    sidebarResetKey = ref(0)
  const entityConditionItems = createConditionItems(),
    visibleTableColumns = entityTableColumns
  const headerConditionItems = computed(() =>
    entityConditionItems.filter((item) => !['project_product', 'module'].includes(String(item.key)))
  )
  const rows = ref<EntityRecord[]>([]),
    listLoading = ref(false),
    loadError = ref(false),
    enumsLoading = ref(false),
    enumsError = ref(false),
    usersLoading = ref(false),
    usersError = ref(false)
  const editorRef = ref<EntityEditorHandle | null>(null),
    batchRef = ref<BatchPanelHandle | null>(null),
    fieldsRef = ref<RecordPanelHandle | null>(null),
    logsRef = ref<RecordPanelHandle | null>(null)
  const entitySaving = ref(false),
    writingIds = reactive(new Set<number>()),
    deletingIds = reactive(new Set<number>()),
    statusIds = reactive(new Set<number>())
  const pagination = usePagination(doRefresh, listLoading)
  let listRequest = 0,
    enumRequest = 0,
    userRequest = 0,
    context = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useEntityScope(reset, resume)
  function getSearchItem(key: string) {
    return entityConditionItems.find((item) => item.key === key)
  }
  function getSearchItemValue(key: string) {
    return optionId(getSearchItem(key)?.value)
  }
  const isBusy = (id: number) => writingIds.has(id) || deletingIds.has(id) || statusIds.has(id)
  function closePanels() {
    ++context
    editorRef.value?.close()
    batchRef.value?.close()
    fieldsRef.value?.close()
    logsRef.value?.close()
    confirmation?.close()
    confirmation = null
  }
  function reset() {
    ++listRequest
    ++enumRequest
    ++userRequest
    closePanels()
    aliases.clear()
    rows.value = []
    pagination.setTotalSize(0)
    listLoading.value = false
    loadError.value = false
    enumsLoading.value = false
    enumsError.value = false
    usersLoading.value = false
    usersError.value = false
    setUpdateUserOptions(entityConditionItems, [])
  }
  function resume() {
    void doRefresh()
    void loadEnums()
    void loadUsers()
    void aliases.load(getSearchItemValue('project_product'))
  }
  async function loadEnums() {
    if (!scope.isActive()) return
    const request = ++enumRequest,
      version = scope.snapshot()
    enumsLoading.value = true
    enumsError.value = false
    try {
      await enumStore.getEnum()
    } catch (loadFailure0) {
      if (request === enumRequest && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), enumsError.value = true)
    } finally {
      if (request === enumRequest) enumsLoading.value = false
    }
  }
  async function loadUsers() {
    if (!scope.isActive()) return
    const request = ++userRequest,
      version = scope.snapshot()
    usersLoading.value = true
    usersError.value = false
    try {
      const response = await getUserName()
      if (request === userRequest && scope.current(version))
        setUpdateUserOptions(entityConditionItems, response.data || [])
    } catch (loadFailure1) {
      if (request === userRequest && scope.current(version)) (reportLoadError(loadFailure1, "加载失败，请重试", false), usersError.value = true)
    } finally {
      if (request === userRequest) usersLoading.value = false
    }
  }
  async function doRefresh() {
    if (!scope.isActive()) return
    const request = ++listRequest,
      version = scope.snapshot(),
      query = getFormItems(entityConditionItems)
    query.project_product = getSearchItemValue('project_product')
    query.module = getSearchItemValue('module')
    Object.keys(query).forEach((key) => {
      if (query[key] === '' || query[key] === null || query[key] === undefined) delete query[key]
    })
    Object.assign(query, { page: pagination.page, pageSize: pagination.pageSize })
    listLoading.value = true
    loadError.value = false
    try {
      const response = await getDataFactoryEntity(query)
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
  function onNavigationFilterChange({
    projectProduct,
    module,
  }: {
    projectProduct: string | number | null
    module: string | number | null
  }) {
    closePanels()
    const previous = getSearchItemValue('project_product'),
      product = getSearchItem('project_product'),
      moduleItem = getSearchItem('module')
    if (product) product.value = projectProduct ?? ''
    if (moduleItem) moduleItem.value = module ?? ''
    if (String(previous) !== String(projectProduct)) {
      const item = getSearchItem('datasource_alias')
      if (item) item.value = []
      void aliases.load(projectProduct)
    }
    return onSearch()
  }
  function onResetSearch() {
    closePanels()
    entityConditionItems.forEach((item) => {
      item.value = item.multiple ? [] : ''
    })
    aliases.clear()
    sidebarResetKey.value++
    return onSearch()
  }
  function defaults() {
    return (
      navigationCreateRef.value?.getCreateDefaults() || {
        projectProduct: getSearchItemValue('project_product'),
        module: getSearchItemValue('module'),
      }
    )
  }
  function openEntity(record?: EntityRecord) {
    if (!scope.isActive() || entitySaving.value || (record && isBusy(record.id))) return
    fieldsRef.value?.close()
    editorRef.value?.open(record, defaults())
  }
  function openBatchGenerate() {
    if (scope.isActive() && !entitySaving.value) batchRef.value?.open(defaults())
  }
  function openFields(record: EntityRecord) {
    if (!scope.isActive() || entitySaving.value || isBusy(record.id)) return
    editorRef.value?.close()
    fieldsRef.value?.open(record)
  }
  function openStatusLogs(record: EntityRecord) {
    if (scope.isActive()) logsRef.value?.open(record)
  }
  function onEntitySaving(id: number | null, pending: boolean) {
    entitySaving.value = pending
    if (id !== null) onFieldSaving(id, pending)
  }
  function onFieldSaving(id: number, pending: boolean) {
    if (pending) writingIds.add(id)
    else writingIds.delete(id)
  }
  function entityStatusTooltip(record: EntityRecord) {
    return statusTooltip(record, enumStore.data_factory_entity_status_change_source || [])
  }
  function statusSourceTitle(value: unknown) {
    return (
      (enumStore.data_factory_entity_status_change_source || []).find(
        (item) => Number(item.key) === Number(value)
      )?.title || '历史来源未知'
    )
  }
  async function switchEntityStatus(newValue: boolean, id: number): Promise<boolean> {
    if (!scope.isActive() || entitySaving.value || isBusy(id)) return false
    const version = scope.snapshot(),
      current = context,
      status = newValue ? 1 : 0
    statusIds.add(id)
    try {
      const response = await putDataFactoryEntityStatus({ id, status })
      if (!scope.current(version) || current !== context || response.code !== 200) return false
      const row = rows.value.find((row) => row.id === id)
      if (row) row.status = status
      Message.success(response.msg)
      await doRefresh()
      return true
    } catch {
      return false
    } finally {
      statusIds.delete(id)
    }
  }
  function removeEntity(record: EntityRecord) {
    if (!scope.isActive() || entitySaving.value || confirmation || isBusy(record.id)) return
    const id = record.id,
      name = record.name,
      current = context,
      version = scope.snapshot()
    const dialog = Modal.confirm({
      title: '删除实体',
      content: `确认删除 ${name}？`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!scope.current(version) || current !== context || isBusy(id)) return false
        deletingIds.add(id)
        try {
          await deleteDataFactoryEntity(id)
          if (current === context && scope.current(version)) {
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
