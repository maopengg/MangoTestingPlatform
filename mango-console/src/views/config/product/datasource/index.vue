<template>
  <TableBody ref="tableBody" class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ datasourceDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护产品级逻辑数据库，并按环境绑定全局数据库配置</div>
        </div>
        <a-space v-if="!embedded" class="mango-detail-actions" wrap>
          <a-button
            class="mango-back-button"
            size="small"
            @click="doResetSearch"
            data-testid="qa-views-config-product-datasource-button-返回"
            >返回</a-button
          >
        </a-space>
      </div>
    </template>

    <template #default>
      <div class="mango-datasource-workbench-scroll">
        <div class="mango-datasource-workbench">
          <section class="mango-section-card mango-datasource-master">
            <div class="mango-section-title">
              <div class="mango-section-title__main">
                <h2>逻辑数据库</h2>
                <p>选择数据库后，在右侧维护对应的环境绑定关系</p>
              </div>
              <a-button
                size="small"
                type="primary"
                @click="onAdd"
                data-testid="qa-views-config-product-datasource-button-新增"
                >新增</a-button
              >
            </div>

            <template v-if="listFailed"><a-button size="small" :loading="listLoading" @click="doRefresh"
                >重新加载</a-button></template>
            <MangoPanelSpin
              class="mango-datasource-card-loading mango-native-scrollbar"
              :loading="listLoading"
            >
              <div v-if="rows.length" class="mango-datasource-card-list">
                <article
                  v-for="record in rows"
                  :key="record.id"
                  class="mango-datasource-card"
                  :class="{
                    'mango-datasource-card--active': String(record.id) === String(selectedId),
                  }"
                  :aria-selected="String(record.id) === String(selectedId)"
                  role="button"
                  tabindex="0"
                  @click="onSelectDatasource(record)"
                  @keydown.enter="onSelectDatasource(record)"
                  @keydown.space.prevent="onSelectDatasource(record)"
                >
                  <div class="mango-datasource-card__header">
                    <div class="mango-datasource-card__identity">
                      <span class="mango-datasource-card__name" :title="record.name">{{
                        record.name
                      }}</span>
                      <span class="mango-datasource-card__id mango-muted-text"
                        >ID {{ record.id }}</span
                      >
                    </div>
                    <span
                      :title="record.status === 1 ? '点击停用' : '点击启用'"
                      @click.stop
                      @keydown.stop
                    >
                      <a-switch
                        size="small"
                        :before-change="(checked) => onStatusChange(record, checked)"
                        :loading="aliasUpdating.has(record.id)"
                        :model-value="record.status === 1"
                      />
                    </span>
                  </div>
                  <div class="mango-datasource-card__tags">
                    <a-tag :color="enumStore.colors[record.source_category]" size="small">
                      {{ getDataSourceCategoryName(record.source_category) }}
                    </a-tag>
                    <a-tag :color="enumStore.colors[record.db_type]" size="small">
                      {{ getDatabaseTypeName(record.db_type) }}
                    </a-tag>
                  </div>
                  <p
                    v-if="record.description"
                    class="mango-datasource-card__description"
                    :title="record.description"
                  >
                    {{ record.description }}
                  </p>
                  <div class="mango-datasource-card__footer" @click.stop>
                    <MangoTableActions
                      :max-inline="3"
                      :actions="[
                        { label: '编辑', onClick: () => onUpdate(record) },
                        { label: '删除', danger: true, onClick: () => onDelete(record) },
                      ]"
                    />
                  </div>
                </article>
              </div>
              <div v-else class="mango-empty-state">暂无逻辑数据库</div>
            </MangoPanelSpin>
          </section>

          <section class="mango-section-card mango-datasource-detail">
            <div class="mango-section-title mango-binding-title">
              <div class="mango-section-title__main">
                <h2>数据库绑定关系</h2>
                <p v-if="selectedId">
                  当前逻辑数据库：{{ selectedDatasource?.name }}，按测试环境绑定全局数据库配置
                </p>
                <p v-else>请先选择左侧逻辑数据库</p>
              </div>
              <a-space>
                <a-button
                  size="small"
                  :disabled="!selectedDatasource"
                  @click="onOpenQueryDrawer(selectedDatasource)"
                  >查询</a-button
                >
                <a-button
                  size="small"
                  type="primary"
                  :disabled="!selectedId"
                  @click="onAddBinding"
                  data-testid="qa-views-config-product-datasource-button-新增绑定"
                >
                  新增绑定
                </a-button>
              </a-space>
            </div>

            <template v-if="bindingsFailed"><a-button size="small" :loading="bindingsLoading" @click="loadDatasourceBindings"
                >重新加载</a-button></template>
            <a-tabs v-model:active-key="detailTab" class="mango-datasource-detail-tabs">
              <a-tab-pane key="bindings" title="环境绑定">
                <div v-if="selectedId" class="mango-binding-table">
                  <a-table
                    :bordered="false"
                    :columns="bindingColumns"
                    :data="bindings"
                    :loading="bindingsLoading"
                    :pagination="false"
                    :scroll="{ x: 1230 }"
                    row-key="id"
                    size="small"
                  >
                    <template #columns>
                      <a-table-column
                        v-for="item of bindingColumns"
                        :key="item.key"
                        :align="item.align"
                        :data-index="item.key"
                        :ellipsis="item.ellipsis"
                        :fixed="item.fixed"
                        :title="item.title"
                        :tooltip="item.tooltip"
                        :width="item.width"
                      >
                        <template v-if="item.key === 'environment'" #cell="{ record }">
                          <a-tag :color="enumStore.colors[record.environment]" size="small">
                            {{ getEnvironmentName(record) }}
                          </a-tag>
                        </template>
                        <template v-else-if="item.key === 'database_alias'" #cell="{ record }">
                          {{ bindingDataSource(record)?.display_name || '-' }}
                        </template>
                        <template v-else-if="item.key === 'data_source'" #cell="{ record }">
                          {{ dataSourceConnectionSummary(bindingDataSource(record)) }}
                        </template>
                        <template v-else-if="item.key === 'host'" #cell="{ record }">
                          {{ bindingDataSource(record)?.host || '-' }}
                        </template>
                        <template v-else-if="item.key === 'database_name'" #cell="{ record }">
                          {{
                            record.database_name ||
                            (record.redis_db != null ? `DB ${record.redis_db}` : '未选默认库')
                          }}{{ record.schema_name ? ` / ${record.schema_name}` : '' }}
                        </template>
                        <template v-else-if="item.key === 'db_c_status'" #cell="{ record }">
                          <a-switch
                            :before-change="
                              (checked) => onBindingPermissionChange(record, 'db_c_status', checked)
                            "
                            :loading="bindingUpdating.has(record.id)"
                            :model-value="record.db_c_status === 1"
                          />
                        </template>
                        <template v-else-if="item.key === 'db_rud_status'" #cell="{ record }">
                          <a-switch
                            :before-change="
                              (checked) =>
                                onBindingPermissionChange(record, 'db_rud_status', checked)
                            "
                            :disabled="record.environment === 2 && record.db_rud_status !== 1"
                            :loading="bindingUpdating.has(record.id)"
                            :model-value="record.db_rud_status === 1"
                            :title="record.environment === 2 ? '生产环境禁止开启写入权限' : ''"
                          />
                        </template>
                        <template v-else-if="item.key === 'actions'" #cell="{ record }">
                          <MangoTableActions
                            :actions="[
                              {
                                label: '编辑',
                                onClick: () => onEditBinding(record),
                              },
                              {
                                label: '解绑',
                                danger: true,
                                onClick: () => onUnbindDatasource(record),
                              },
                            ]"
                          />
                        </template>
                      </a-table-column>
                    </template>
                  </a-table>
                </div>
                <div v-else class="mango-empty-state mango-binding-empty">请选择一个逻辑数据库</div>
              </a-tab-pane>
              <a-tab-pane v-if="supportsDatasourceTables" key="tables" title="数据表">
                <ProductDataSourceTables
                  v-if="selectedId"
                  :alias-id="selectedId"
                  :product-id="String(productId || '')"
                  :bindings="bindings"
                />
              </a-tab-pane>
            </a-tabs>
          </section>
        </div>
      </div>
    </template>
  </TableBody>

  <LogicalSourceEditor
    ref="aliasEditorRef"
    :product-id="productId"
    :options-loading="optionsLoading"
    @saved="doRefresh"
  />
  <LogicalBindingEditor
    ref="bindingEditorRef"
    :alias="selectedDatasource"
    :product-id="productId"
    :bindings="bindings"
    @saved="loadDatasourceBindings"
  />
  <LogicalSourceQueryDrawer ref="queryRef" :product-id="productId" :alias-id="selectedId" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    deleteDataFactoryDatasourceAlias,
    deleteDataFactoryDatasourceBinding,
    getDataFactoryDatasourceAlias,
    getDataFactoryDatasourceBinding,
    putDataFactoryDatasourceAlias,
    putDataFactoryDatasourceBinding,
  } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { getOptionId } from '@/utils/business-format'
  import ProductDataSourceTables from './components/ProductDataSourceTables.vue'
  import LogicalSourceEditor from './components/LogicalSourceEditor.vue'
  import LogicalBindingEditor from './components/LogicalBindingEditor.vue'
  import LogicalSourceQueryDrawer from './components/LogicalSourceQueryDrawer.vue'
  import { useProductDatasourceScope } from './composables/useProductDatasourceScope'
  import { sortLogicalDatasources, bindingColumns } from './config'
  import { bindingDataSource, connectionName, sourceLabel } from './form'
  import type {
    EntityId,
    LogicalSource,
    LogicalBinding,
    SourceConnection,
    AliasEditorHandle,
    BindingEditorHandle,
    QueryDrawerHandle,
  } from './types'
  const props = defineProps<{
    embedded?: boolean
    projectProductId?: EntityId
    projectProductName?: string
    datasourceId?: EntityId
  }>()
  const route = useRoute(),
    enumStore = useEnum()
  const productId = computed<EntityId | null>(() => {
    const value: unknown = getOptionId(props.projectProductId ?? route.query.id)
    return (typeof value === 'string' && value !== '') || typeof value === 'number' ? value : null
  })
  const productName = computed(
    () =>
      props.projectProductName ?? (typeof route.query.name === 'string' ? route.query.name : '-')
  )
  const datasourceDetailTitle = computed(
    () => `产品逻辑数据库 / ${productId.value ?? '-'} / ${productName.value}`
  )
  const rows = ref<LogicalSource[]>([]),
    listLoading = ref(false),
    listFailed = ref(false),
    optionsLoading = ref(false)
  const selectedId = ref<number | null>(null)
  const selectedDatasource = computed(
    () => rows.value.find((item) => item.id === selectedId.value) ?? null
  )
  const bindings = ref<LogicalBinding[]>([]),
    bindingsLoading = ref(false),
    bindingsFailed = ref(false)
  const detailTab = ref('bindings')
  const aliasEditorRef = ref<AliasEditorHandle | null>(null),
    bindingEditorRef = ref<BindingEditorHandle | null>(null),
    queryRef = ref<QueryDrawerHandle | null>(null)
  const aliasUpdating = reactive(new Set<number>()),
    bindingUpdating = reactive(new Set<number>())
  let listRequest = 0,
    bindingRequest = 0,
    enumRequest = 0,
    selectionVersion = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useProductDatasourceScope(() => [productId.value], reset, resume)
  const supportsDatasourceTables = computed(() => {
    const datasource = selectedDatasource.value
    if (datasource?.db_type == null) return false
    return [0, 1, 2, 3, 4, 20].includes(Number(datasource.db_type))
  })
  watch(
    supportsDatasourceTables,
    (supported) => {
      if (!supported) detailTab.value = 'bindings'
    },
    { flush: 'sync' }
  )
  function closeWindows() {
    aliasEditorRef.value?.close()
    bindingEditorRef.value?.close()
    queryRef.value?.close()
    confirmation?.close()
    confirmation = null
  }
  function reset() {
    ++listRequest
    ++bindingRequest
    ++enumRequest
    ++selectionVersion
    rows.value = []
    selectedId.value = null
    bindings.value = []
    listLoading.value = false
    bindingsLoading.value = false
    optionsLoading.value = false
    listFailed.value = false
    bindingsFailed.value = false
    closeWindows()
  }
  function resume() {
    void doRefresh()
    void loadEnums()
  }
  async function loadEnums() {
    if (!scope.isActive()) return
    const request = ++enumRequest
    optionsLoading.value = true
    try {
      await enumStore.getEnum()
    } catch {
    } finally {
      if (request === enumRequest) optionsLoading.value = false
    }
  }
  async function doRefresh() {
    if (!scope.isActive() || productId.value === null) return
    const current = ++listRequest,
      version = scope.snapshot(),
      product = productId.value
    listLoading.value = true
    listFailed.value = false
    try {
      const response = await getDataFactoryDatasourceAlias({ project_product: product })
      if (current !== listRequest || !scope.current(version)) return
      rows.value = sortLogicalDatasources<LogicalSource>(response.data || [])
      const requested =
        selectedId.value ?? (props.datasourceId === undefined ? null : Number(props.datasourceId))
      selectedId.value =
        rows.value.find((item) => item.id === requested)?.id ?? rows.value[0]?.id ?? null
    } catch (loadFailure0) {
      if (current === listRequest && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), listFailed.value = true)
    } finally {
      if (current === listRequest) listLoading.value = false
    }
  }
  function onSelectDatasource(record: LogicalSource) {
    if (scope.isActive()) selectedId.value = record.id
  }
  watch(
    () => props.datasourceId,
    (value) => {
      const id = Number(value)
      if (rows.value.some((item) => item.id === id)) selectedId.value = id
    }
  )
  watch(
    selectedDatasource,
    (value, previous) => {
      ++selectionVersion
      ++bindingRequest
      bindings.value = []
      bindingsLoading.value = false
      bindingsFailed.value = false
      if (value?.id !== previous?.id) closeWindows()
      if (value) void loadDatasourceBindings()
    },
    { flush: 'sync' }
  )
  async function loadDatasourceBindings() {
    if (!scope.isActive() || selectedId.value === null) return
    const current = ++bindingRequest,
      version = scope.snapshot(),
      id = selectedId.value
    bindingsLoading.value = true
    bindingsFailed.value = false
    try {
      const response = await getDataFactoryDatasourceBinding({
        datasource_alias: id,
        page: 1,
        pageSize: 999,
      })
      if (current === bindingRequest && scope.current(version)) bindings.value = response.data || []
    } catch (loadFailure1) {
      if (current === bindingRequest && scope.current(version)) (reportLoadError(loadFailure1, "加载失败，请重试", false), bindingsFailed.value = true)
    } finally {
      if (current === bindingRequest) bindingsLoading.value = false
    }
  }
  function getDatabaseTypeName(value: number) {
    return enumStore.data_source_type?.find((item) => Number(item.key) === value)?.title ?? value
  }
  function getDataSourceCategoryName(value: number) {
    return (
      enumStore.data_source_category?.find((item) => Number(item.key) === value)?.title ?? value
    )
  }
  function getEnvironmentName(record: LogicalBinding) {
    return (
      enumStore.environment_type?.find((item) => Number(item.key) === record.environment)?.title ??
      `环境${record.environment}`
    )
  }
  function dataSourceConnectionSummary(source: SourceConnection | null) {
    return source ? `${connectionName(source)} · ${getDatabaseTypeName(source.db_type)}` : '-'
  }
  function doResetSearch() {
    window.history.back()
  }
  function onAdd() {
    aliasEditorRef.value?.open()
  }
  function onUpdate(record: LogicalSource) {
    if (!aliasUpdating.has(record.id)) aliasEditorRef.value?.open(record)
  }
  function onAddBinding() {
    bindingEditorRef.value?.open()
  }
  function onEditBinding(record: LogicalBinding) {
    if (!bindingUpdating.has(record.id)) bindingEditorRef.value?.open(record)
  }
  function onOpenQueryDrawer(record: LogicalSource | null) {
    if (record) queryRef.value?.open(record)
  }
  function confirmRemoval(
    id: number,
    title: string,
    content: string,
    pending: Set<number>,
    remove: () => Promise<unknown>,
    refresh: () => Promise<void>
  ) {
    if (!scope.isActive() || confirmation || pending.has(id)) return
    const version = scope.snapshot(),
      selection = selectionVersion
    const dialog = Modal.confirm({
      title,
      content,
      cancelText: '取消',
      okText: title === '解绑数据库' ? '解绑' : '删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!scope.current(version) || selection !== selectionVersion || pending.has(id))
          return false
        pending.add(id)
        try {
          await remove()
          if (scope.current(version)) {
            Message.success('操作成功')
            await refresh()
          }
          return true
        } catch {
          return false
        } finally {
          pending.delete(id)
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  function onDelete(record: LogicalSource) {
    const id = record.id
    confirmRemoval(
      id,
      '删除产品逻辑源',
      `确认删除 ${record.name}？删除后会影响引用它的数据实体、API SQL 和 UI SQL 配置。`,
      aliasUpdating,
      () => deleteDataFactoryDatasourceAlias(id),
      doRefresh
    )
  }
  function onUnbindDatasource(record: LogicalBinding) {
    const id = record.id
    confirmRemoval(
      id,
      '解绑数据库',
      `确认解除「${selectedDatasource.value?.name}」在「${getEnvironmentName(
        record
      )}」与「${sourceLabel(bindingDataSource(record))}」的绑定关系？`,
      bindingUpdating,
      () => deleteDataFactoryDatasourceBinding(id),
      loadDatasourceBindings
    )
  }
  async function onStatusChange(record: LogicalSource, checked: boolean): Promise<boolean> {
    if (!scope.isActive() || aliasUpdating.has(record.id) || productId.value === null) return false
    const id = record.id,
      version = scope.snapshot(),
      payload = {
        project_product:
          typeof record.project_product === 'object'
            ? record.project_product.id
            : record.project_product ?? productId.value,
        name: record.name,
        source_category: record.source_category,
        db_type: record.db_type,
        description: record.description || null,
        id,
        status: checked ? 1 : 0,
      }
    aliasUpdating.add(id)
    ++listRequest
    listLoading.value = false
    try {
      await putDataFactoryDatasourceAlias(payload)
      if (!scope.current(version)) return false
      const row = rows.value.find((item) => item.id === id)
      if (row) row.status = payload.status
      Message.success('操作成功')
      return true
    } catch {
      return false
    } finally {
      aliasUpdating.delete(id)
    }
  }
  async function onBindingPermissionChange(
    record: LogicalBinding,
    field: 'db_c_status' | 'db_rud_status',
    checked: boolean
  ): Promise<boolean> {
    if (
      !scope.isActive() ||
      bindingUpdating.has(record.id) ||
      (field === 'db_rud_status' && checked && record.environment === 2)
    )
      return false
    const id = record.id,
      version = scope.snapshot(),
      selection = selectionVersion,
      status = checked ? 1 : 0
    bindingUpdating.add(id)
    ++bindingRequest
    bindingsLoading.value = false
    try {
      await putDataFactoryDatasourceBinding({ id, [field]: status })
      if (!scope.current(version) || selection !== selectionVersion) return false
      const row = bindings.value.find((item) => item.id === id)
      if (row) row[field] = status
      Message.success('操作成功')
      return true
    } catch {
      return false
    } finally {
      bindingUpdating.delete(id)
    }
  }
  onMounted(resume)
</script>
<style scoped>
  .mango-datasource-workbench-scroll {
    height: calc(100% - var(--m-page-gap));
    min-height: 0;
    margin-top: var(--m-page-gap);
    overflow-x: auto;
    overflow-y: hidden;
  }

  .mango-datasource-workbench {
    display: grid;
    grid-template-columns: 320px minmax(720px, 1fr);
    gap: var(--m-page-gap);
    min-width: 1052px;
    height: 100%;
    min-height: 0;
    grid-template-rows: minmax(0, 1fr);
  }

  .mango-datasource-workbench > .mango-section-card + .mango-section-card {
    margin-top: 0;
  }

  .mango-datasource-master,
  .mango-datasource-detail {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
  }

  .mango-datasource-detail-tabs {
    display: flex;
    flex: 1;
    min-height: 0;
    flex-direction: column;

    :deep(.arco-tabs-nav) {
      flex-shrink: 0;
    }

    :deep(.arco-tabs-content) {
      flex: 1;
      min-height: 0;
      padding-top: 0;
      overflow-x: hidden;
      overflow-y: auto;
      overscroll-behavior-y: contain;
    }
  }

  .mango-datasource-card-loading {
    display: block;
    min-height: 0;
    flex: 1;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior-y: contain;
    scrollbar-gutter: stable;
  }

  .mango-datasource-card-list {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
  }

  .mango-datasource-card {
    position: relative;
    padding: var(--m-space-md);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    cursor: pointer;
    transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
  }

  .mango-datasource-card:hover,
  .mango-datasource-card:focus-visible {
    border-color: var(--m-primary-border);
    outline: none;
    box-shadow: var(--m-shadow-sm);
  }

  .mango-datasource-card--active {
    border-color: var(--m-primary);
    background: var(--m-primary-soft);
    box-shadow: inset 3px 0 0 var(--m-primary);
  }

  .mango-datasource-card__header,
  .mango-datasource-card__identity,
  .mango-datasource-card__tags,
  .mango-datasource-card__footer {
    display: flex;
    align-items: center;
  }

  .mango-datasource-card__header {
    justify-content: space-between;
    gap: var(--m-space-sm);
  }

  .mango-datasource-card__identity {
    min-width: 0;
    flex: 1;
    gap: var(--m-space-sm);
  }

  .mango-datasource-card__name {
    overflow: hidden;
    color: var(--m-text);
    font-size: var(--m-font-body);
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-datasource-card__id {
    flex: none;
    font-size: var(--m-font-caption);
    white-space: nowrap;
  }

  .mango-datasource-card__tags {
    flex-wrap: wrap;
    gap: var(--m-space-xs);
    margin-top: var(--m-space-sm);
  }

  .mango-datasource-card__description {
    display: -webkit-box;
    margin: var(--m-space-sm) 0 0;
    overflow: hidden;
    color: var(--m-text-2);
    font-size: var(--m-font-caption);
    line-height: var(--m-line-caption);
    overflow-wrap: anywhere;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .mango-datasource-card__footer {
    justify-content: flex-end;
    margin-top: var(--m-space-sm);
    padding-top: var(--m-space-xs);
    border-top: 1px solid var(--m-border);
  }

  .mango-binding-title {
    gap: var(--m-page-gap);
  }

  .mango-binding-table {
    min-height: 0;
    flex: 1;
    overflow: hidden;
  }

  .mango-binding-empty {
    display: flex;
    min-height: 240px;
    flex: 1;
    align-items: center;
    justify-content: center;
  }

  @container (max-width: 1099px) {
    .mango-datasource-workbench {
      grid-template-columns: 300px minmax(700px, 1fr);
      min-width: 1012px;
    }
  }
</style>
