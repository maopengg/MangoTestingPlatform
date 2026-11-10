<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="数据工厂 / 场景模板" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
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
              <template v-else-if="item.type === 'select' && item.key === 'entity'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="{ value: 'id', label: 'display_name' }"
                  :options="searchEntityOptions"
                  :loading="entityLoading"
                  :filter-option="filterEntityOption"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'cleanup_strategy'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_cleanup_strategy"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'usage_scope'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_template_usage_scope"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
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
          <a-button
            size="small"
            type="primary"
            @click="openTemplate()"
            data-testid="qa-views-data-factory-template-button-新增场景模板"
            >新增场景模板</a-button
          >
        </template>
        
        <a-table
          class="mango-native-scroll-table"
          :scroll="{ x: templateScrollX, y: '100%' }"
          :bordered="false"
          :columns="visibleTableColumns"
          :data="rows"
          :loading="listLoading"
          :pagination="false"
          :row-key="'id'"
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
              <template v-else-if="item.key === 'entity'" #cell="{ record }">
                {{ formatEntityLabel(record.entity) }}
              </template>
              <template v-else-if="item.key === 'cleanup_strategy'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.cleanup_strategy]" size="small">
                  {{ enumTitle(enumStore.data_factory_cleanup_strategy, record.cleanup_strategy) }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'is_default'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.is_default ? 1 : 0]" size="small">
                  {{ record.is_default ? '默认使用' : '手动选择' }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'usage_scope'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.usage_scope]" size="small">
                  {{
                    enumTitle(
                      enumStore.data_factory_template_usage_scope,
                      Number(record.usage_scope) === 2 ? 2 : 1
                    )
                  }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'config_status'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.config_status ?? 0]" size="small">
                  {{
                    enumTitle(
                      enumStore.data_factory_template_config_status,
                      record.config_status ?? 0
                    )
                  }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-switch
                  :beforeChange="(newValue) => switchTemplateStatus(newValue, record.id)"
                  :loading="busyIds.has(record.id)"
                  :disabled="busyIds.has(record.id)"
                  :model-value="record.status === 1"
                />
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
                <MangoTableActions :actions="templateActions(record)" />
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <TemplateEditor ref="editorRef" @saved="doRefresh" @saving-change="onSavingChange" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    deleteDataFactoryTemplate,
    getDataFactoryTemplate,
    postDataFactoryTemplateCopy,
    putDataFactoryTemplateStatus,
  } from '@/api/data-factory'
  import { getUserName } from '@/api/user/user'
  import { usePagination } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePageData } from '@/store/page-data'
  import { getFormItems } from '@/utils/datacleaning'
  import { setUpdateUserOptions } from '@/utils/update-user'
  import { formatProjectProductPath, formatModulePath } from '@/utils/business-format'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import TemplateEditor from './components/TemplateEditor.vue'
  import {
    createConditionItems,
    templateTableColumns,
    templateScrollX,
    enumFieldNames,
    statusOptions,
  } from './config'
  import { optionId, enumTitle, filterEntityOption, formatEntityLabel } from './form'
  import { useTemplateScope } from './composables/useTemplateScope'
  import { useTemplateEntities } from './composables/useTemplateEntities'
  import type { TemplateRecord, EditorHandle, Id } from './types'

  const enumStore = useEnum(),
    pageData = usePageData(),
    router = useRouter()
  const templateConditionItems = createConditionItems(),
    visibleTableColumns = templateTableColumns
  const headerConditionItems = computed(() =>
    templateConditionItems.filter(
      (item) => !['project_product', 'module'].includes(String(item.key))
    )
  )
  const rows = ref<TemplateRecord[]>([]),
    listLoading = ref(false),
    loadError = ref(false)
  const pagination = usePagination(doRefresh, listLoading),
    sidebarResetKey = ref(0)
  const navigationCreateRef = ref<NavigationCreateSource | null>(null),
    editorRef = ref<EditorHandle | null>(null)
  const busyIds = reactive(new Set<number>()),
    actionLoading = reactive(new Map<number, string>())
  const optionsLoading = ref(false),
    optionsError = ref(false),
    navigatingId = ref<number | null>(null)
  const entities = useTemplateEntities(),
    { options: searchEntityOptions, loading: entityLoading, error: entityError } = entities
  let listRequest = 0,
    optionsRequest = 0,
    context = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useTemplateScope(reset, resume)
  function getSearchItem(key: string) {
    return templateConditionItems.find((item) => item.key === key)
  }
  function getSearchItemValue(key: string) {
    return optionId(getSearchItem(key)?.value)
  }
  function reset() {
    ++listRequest
    ++optionsRequest
    ++context
    confirmation?.close()
    confirmation = null
    editorRef.value?.close()
    entities.clear()
    rows.value = []
    pagination.setTotalSize(0)
    listLoading.value = false
    loadError.value = false
    optionsLoading.value = false
    optionsError.value = false
    setUpdateUserOptions(templateConditionItems, [])
  }
  function resume() {
    void doRefresh()
    void loadOptions()
    void loadSearchEntities()
  }
  async function loadOptions() {
    if (!scope.isActive()) return
    const request = ++optionsRequest,
      version = scope.snapshot()
    optionsLoading.value = true
    optionsError.value = false
    const results = await Promise.allSettled([enumStore.getEnum(), getUserName()])
    if (request !== optionsRequest || !scope.current(version)) return
    const users = results[1]
    if (users.status === 'fulfilled')
      setUpdateUserOptions(templateConditionItems, users.value.data || [])
    optionsError.value = results.some((result) => result.status === 'rejected')
    optionsLoading.value = false
  }
  async function doRefresh() {
    if (!scope.isActive()) return
    const request = ++listRequest,
      version = scope.snapshot(),
      query = getFormItems(templateConditionItems)
    query.project_product = getSearchItemValue('project_product')
    query.module = getSearchItemValue('module')
    Object.keys(query).forEach((key) => {
      if (query[key] === '' || query[key] == null) delete query[key]
    })
    Object.assign(query, { page: pagination.page, pageSize: pagination.pageSize })
    listLoading.value = true
    loadError.value = false
    try {
      const response = await getDataFactoryTemplate(query)
      if (request === listRequest && scope.current(version)) {
        rows.value = response.data || []
        pagination.setTotalSize(response.totalSize ?? 0)
      }
    } catch (loadFailure0) {
      if (request === listRequest && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (request === listRequest) listLoading.value = false
    }
  }
  function onSearch() {
    pagination.page = 1
    return doRefresh()
  }
  function loadSearchEntities() {
    if (scope.isActive())
      return entities.load(getSearchItemValue('project_product'), getSearchItemValue('module'))
  }
  function onNavigationFilterChange({
    projectProduct,
    module,
  }: {
    projectProduct: Id | null
    module: Id | null
  }) {
    const productItem = getSearchItem('project_product'),
      moduleItem = getSearchItem('module'),
      entityItem = getSearchItem('entity')
    if (productItem) productItem.value = projectProduct ?? ''
    if (moduleItem) moduleItem.value = module ?? ''
    if (entityItem) entityItem.value = []
    ++context
    confirmation?.close()
    confirmation = null
    void loadSearchEntities()
    return onSearch()
  }
  function onResetSearch() {
    templateConditionItems.forEach((item) => {
      item.value = item.multiple ? [] : ''
    })
    sidebarResetKey.value++
    ++context
    confirmation?.close()
    confirmation = null
    void loadSearchEntities()
    return onSearch()
  }
  function openTemplate(record?: TemplateRecord) {
    if (!scope.isActive() || (record && busyIds.has(record.id))) return
    editorRef.value?.open(
      record,
      record ? undefined : navigationCreateRef.value?.getCreateDefaults()
    )
  }
  function onSavingChange(id: number | null, pending: boolean) {
    if (id === null) return
    if (pending) busyIds.add(id)
    else busyIds.delete(id)
  }
  async function mutate(
    id: number,
    action: string,
    request: () => Promise<{ msg: string; code?: number }>,
    success?: string
  ): Promise<boolean> {
    if (!scope.isActive() || busyIds.has(id)) return false
    const version = scope.snapshot(),
      current = context
    busyIds.add(id)
    actionLoading.set(id, action)
    try {
      const response = await request()
      if (!scope.current(version) || current !== context) return false
      if (response.code !== undefined && response.code !== 200) return false
      // Update the controlled switch only after the server accepts the change.
      if (action === 'enable' || action === 'disable' || action === 'validate') {
        const record = rows.value.find((item) => item.id === id)
        if (record) record.status = action === 'disable' ? 0 : 1
      }
      Message.success(success || response.msg)
      await doRefresh()
      return true
    } catch {
      return false
    } finally {
      busyIds.delete(id)
      actionLoading.delete(id)
    }
  }
  function copyTemplate(record: TemplateRecord) {
    return mutate(record.id, 'copy', () => postDataFactoryTemplateCopy({ id: record.id }))
  }
  function switchTemplateStatus(value: boolean, id: number) {
    return mutate(id, value ? 'enable' : 'disable', () =>
      putDataFactoryTemplateStatus({ id, status: value ? 1 : 0 })
    )
  }
  function validateTemplate(id: number) {
    return mutate(
      id,
      'validate',
      () => putDataFactoryTemplateStatus({ id, status: 1 }),
      '校验通过，场景模板已启用'
    )
  }
  function removeTemplate(record: TemplateRecord) {
    if (!scope.isActive() || confirmation || busyIds.has(record.id)) return
    const id = record.id,
      version = scope.snapshot(),
      current = context
    const dialog = Modal.confirm({
      title: '删除场景模板',
      content: `确认删除 ${record.name}？`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      onBeforeOk: () =>
        scope.current(version) && current === context
          ? mutate(id, 'delete', () => deleteDataFactoryTemplate(id))
          : Promise.resolve(false),
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  async function openTemplateDetail(record: TemplateRecord) {
    if (!scope.isActive() || navigatingId.value !== null || busyIds.has(record.id)) return
    navigatingId.value = record.id
    try {
      pageData.setRecord(record)
      await router.push({
        path: '/data-factory/template/preview',
        query: { template_id: record.id },
      })
    } catch {
      /* Router errors remain retryable without changing the source record. */
    } finally {
      navigatingId.value = null
    }
  }
  function templateActions(record: TemplateRecord) {
    return [
      {
        label: '场景配置',
        loading: navigatingId.value === record.id,
        disabled: busyIds.has(record.id),
        onClick: () => openTemplateDetail(record),
      },
      { label: '编辑', disabled: busyIds.has(record.id), onClick: () => openTemplate(record) },
      {
        label: '校验',
        hidden: Number(record.config_status) !== 0,
        disabled: busyIds.has(record.id),
        loading: actionLoading.get(record.id) === 'validate',
        onClick: () => validateTemplate(record.id),
      },
      {
        label: '复制',
        disabled: busyIds.has(record.id),
        loading: actionLoading.get(record.id) === 'copy',
        onClick: () => copyTemplate(record),
      },
      {
        label: '删除',
        danger: true,
        disabled: busyIds.has(record.id),
        loading: actionLoading.get(record.id) === 'delete',
        onClick: () => removeTemplate(record),
      },
    ]
  }
  onMounted(resume)
</script>
