<template>
  <a-modal
    v-model:visible="entityVisible"
    :on-before-ok="saveEntity"
    :ok-loading="entitySaving"
    :title="editingId !== null ? '编辑实体' : '新增实体'"
    :width="760"
    :closable="!entitySaving"
    :mask-closable="!entitySaving"
    :esc-to-close="!entitySaving"
    :cancel-button-props="{ disabled: entitySaving }"
    unmount-on-close
    @cancel="close"
  >
    <MangoRequestFeedback v-if="syncError" :message="(syncError)" />
    
    
    <a-form
      :disabled="entitySaving"
      :model="entityForm"
      layout="horizontal"
      class="mango-entity-edit-form"
    >
      <section class="mango-entity-form-section" aria-labelledby="mango-entity-basic-title">
        <h3 id="mango-entity-basic-title" class="mango-entity-form-title">基础信息</h3>
        <div class="mango-entity-form-grid">
          <div>
            <a-form-item label="产品" required>
              <ProjectProductSelect
                v-model="entityForm.project_product"
                :disabled="entitySaving"
                @change="onEntityProjectChange"
              />
            </a-form-item>
          </div>
          <div>
            <a-form-item label="模块名称" required>
              <ProductModuleSelect
                v-model="entityForm.module"
                :disabled="entitySaving"
                :project-product-id="entityForm.project_product"
                :auto-clear="false"
              />
            </a-form-item>
          </div>
          <div>
            <a-form-item label="逻辑数据库" required>
              <a-select
                v-model="entityForm.datasource_alias"
                :field-names="{ value: 'id', label: 'name' }"
                :options="datasourceAliasOptions"
                :loading="aliasLoading"
                allow-clear
                allow-search
                @change="onEntityDatasourceChange"
              />
            </a-form-item>
          </div>
          <div>
            <a-form-item label="实体名称" required
              ><a-input v-model="entityForm.name"
            /></a-form-item>
          </div>
          <div class="mango-entity-form-full">
            <a-form-item label="表名" required>
              <a-input-group class="mango-entity-table-select-group">
                <a-select
                  v-model="entityForm.table_name"
                :loading="entityTableLoading || schemaLoading"
                  :options="entityTableOptions"
                  allow-clear
                  allow-search
                  placeholder="选择逻辑源和环境后自动读取表"
                  class="mango-entity-table-select"
                  @change="onEntityTableChange"
                  data-testid="qa-views-data-factory-entity-select-选择逻辑源和环境后自动读取表"
                />
                <a-button
                  :loading="entityTableRefreshLoading"
                  class="mango-entity-table-refresh"
                  @click="refreshEntityTables"
                  data-testid="qa-views-data-factory-entity-button-清理缓存重试"
                  >清理缓存重试</a-button
                >
              </a-input-group>
            </a-form-item>
          </div>
          <div class="mango-entity-form-full">
            <a-form-item label="Schema"
              ><a-input
                v-model="entityForm.schema_name"
                @input="onSchemaChange"
                placeholder="仅 PostgreSQL 使用，按实际表所属 Schema 填写"
            /></a-form-item>
          </div>
          <div class="mango-entity-form-full">
            <a-form-item label="描述"
              ><a-textarea v-model="entityForm.description" :auto-size="{ minRows: 2, maxRows: 4 }"
            /></a-form-item>
          </div>
        </div>
      </section>
      <section class="mango-entity-form-section" aria-labelledby="mango-entity-rule-title">
        <h3 id="mango-entity-rule-title" class="mango-entity-form-title">字段与操作</h3>
        <div class="mango-entity-form-grid">
          <div
            ><a-form-item label="主键字段"><a-input v-model="entityForm.primary_key" /></a-form-item
          ></div>
          <div
            ><a-form-item label="唯一字段"><a-input v-model="entityForm.unique_key" /></a-form-item
          ></div>
          <div>
            <a-form-item label="创建方式">
              <a-select
                v-model="entityForm.create_type"
                :field-names="enumFieldNames"
                :options="sqlOperationOptions"
                disabled
              />
            </a-form-item>
          </div>
          <div>
            <a-form-item label="删除方式">
              <a-select
                v-model="entityForm.delete_type"
                :field-names="enumFieldNames"
                :options="sqlOperationOptions"
                disabled
              />
            </a-form-item>
          </div>
        </div>
      </section>
      <section class="mango-entity-form-section" aria-labelledby="mango-entity-cleanup-title">
        <h3 id="mango-entity-cleanup-title" class="mango-entity-form-title">清理与同步</h3>
        <div class="mango-entity-form-grid">
          <div>
            <a-form-item label="清理顺序">
              <a-input-number v-model="entityForm.cleanup_order" class="mango-entity-full-width" />
              <template #extra>数值越小越先清理，引用表应排在主表前。</template>
            </a-form-item>
          </div>
          <div>
            <a-form-item label="同步字段规则">
              <a-switch
                v-model="syncFieldsAfterSave"
                checked-text="保存后同步"
                unchecked-text="不同步"
              />
            </a-form-item>
          </div>
        </div>
      </section>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import { reactive, ref, shallowRef } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    postDataFactoryEntity,
    putDataFactoryEntity,
    postDataFactoryDiscoverTables,
    postDataFactoryDiscoverTable,
    postDataFactoryFieldBatchSave,
  } from '@/api/data-factory'
  import useUserStore from '@/store/modules/user'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { enumFieldNames, sqlOperationOptions } from '../config'
  import {
    createEntityDraft,
    entityPayload,
    validateEntity,
    optionId,
    normalizeTable,
    fieldMetadata,
  } from '../form'
  import { useEntityScope } from '../composables/useEntityScope'
  import { useEntityAliases } from '../composables/useEntityAliases'
  import type {
    EntityRecord,
    NavigationDefaults,
    TableOption,
    FieldRecord,
    TableInfo,
    TableSchema,
  } from '../types'
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'saving-change', id: number | null, pending: boolean): void
  }>()
  const userStore = useUserStore()
  const entityForm = reactive(createEntityDraft()),
    editingId = ref<number | null>(null)
  const entityVisible = ref(false),
    entitySaving = ref(false),
    syncFieldsAfterSave = ref(true)
  const entityTableOptions = ref<TableOption[]>([]),
    entityDiscoveredColumns = shallowRef<FieldRecord[]>([])
  const entityTableLoading = ref(false),
    entityTableRefreshLoading = ref(false),
    schemaLoading = ref(false)
  const discoveryError = ref(''),
    syncError = ref('')
  const aliases = useEntityAliases()
  const { options: datasourceAliasOptions, loading: aliasLoading, error: aliasError } = aliases
  let session = 0,
    tableRequest = 0,
    schemaRequest = 0
  const scope = useEntityScope(close)
  function close() {
    ++session
    ++tableRequest
    ++schemaRequest
    entityVisible.value = false
    editingId.value = null
    Object.assign(entityForm, createEntityDraft())
    aliases.clear()
    entityTableOptions.value = []
    entityDiscoveredColumns.value = []
    entityTableLoading.value = false
    entityTableRefreshLoading.value = false
    schemaLoading.value = false
    discoveryError.value = ''
    syncError.value = ''
  }
  function open(record?: EntityRecord, defaults?: NavigationDefaults) {
    if (!scope.isActive() || entitySaving.value) return
    close()
    editingId.value = record?.id ?? null
    Object.assign(entityForm, createEntityDraft(record, defaults))
    syncFieldsAfterSave.value = !record
    entityVisible.value = true
    entityTableOptions.value = record?.table_name
      ? [normalizeTable({ name: record.table_name, schema_name: record.schema_name })]
      : []
    void aliases.load(entityForm.project_product)
    if (record && userStore.selected_environment != null) void loadEntityTables()
  }
  function resetDiscovery() {
    ++tableRequest
    ++schemaRequest
    entityTableOptions.value = []
    entityDiscoveredColumns.value = []
    entityTableLoading.value = false
    entityTableRefreshLoading.value = false
    schemaLoading.value = false
    discoveryError.value = ''
  }
  function onEntityProjectChange(value: unknown) {
    if (entitySaving.value) return
    entityForm.project_product = optionId(value)
    entityForm.module = null
    entityForm.datasource_alias = null
    entityForm.table_name = ''
    entityForm.schema_name = ''
    resetDiscovery()
    void aliases.load(value)
  }
  function onEntityDatasourceChange() {
    if (entitySaving.value) return
    entityForm.table_name = ''
    entityForm.schema_name = ''
    entityForm.primary_key = 'id'
    entityForm.unique_key = ''
    resetDiscovery()
    if (entityForm.datasource_alias !== null && userStore.selected_environment != null)
      void loadEntityTables()
  }
  function discoveryPayload() {
    return {
      datasource_alias_id: optionId(entityForm.datasource_alias),
      project_product: optionId(entityForm.project_product),
      test_env: userStore.selected_environment,
      schema_name: entityForm.schema_name || '',
    }
  }
  function canDiscover() {
    if (userStore.selected_environment == null) {
      Message.error('请先在顶部选择测试环境')
      return false
    }
    return (
      optionId(entityForm.project_product) !== null &&
      optionId(entityForm.datasource_alias) !== null
    )
  }
  async function loadEntityTables(refresh = false): Promise<boolean> {
    if (!entityVisible.value || !scope.isActive() || !canDiscover()) return false
    const request = ++tableRequest,
      current = session,
      version = scope.snapshot(),
      payload = { ...discoveryPayload(), refresh }
    entityTableLoading.value = true
    entityTableRefreshLoading.value = refresh
    discoveryError.value = ''
    try {
      const response = await postDataFactoryDiscoverTables(payload)
      if (request !== tableRequest || current !== session || !scope.current(version)) return false
      entityTableOptions.value = (response.data || []).map((item: string | TableInfo) =>
        normalizeTable(item)
      )
      if (refresh) Message.success('表名缓存已清理并重新加载')
      return true
    } catch (loadFailure0) {
      if (request === tableRequest && current === session && scope.current(version))
        void (reportLoadError(loadFailure0, "表名加载失败，请重试", false), discoveryError.value = '表名加载失败，请重试')
      return false
    } finally {
      if (request === tableRequest) {
        entityTableLoading.value = false
        entityTableRefreshLoading.value = false
      }
    }
  }
  function refreshEntityTables() {
    if (!entitySaving.value) return loadEntityTables(true)
  }
  async function onEntityTableChange(tableName: string) {
    if (entitySaving.value) return
    entityDiscoveredColumns.value = []
    const request = ++schemaRequest
    schemaLoading.value = false
    if (!tableName || !canDiscover() || !entityVisible.value || !scope.isActive()) return
    const current = session,
      version = scope.snapshot(),
      payload = { ...discoveryPayload(), table_name: tableName },
      nameBefore = entityForm.name
    schemaLoading.value = true
    discoveryError.value = ''
    try {
      const response = await postDataFactoryDiscoverTable(payload)
      if (
        request !== schemaRequest ||
        current !== session ||
        !scope.current(version) ||
        entityForm.table_name !== tableName
      )
        return
      const schema: TableSchema = response.data || {}
      entityForm.schema_name = schema.schema_name || ''
      entityDiscoveredColumns.value = schema.columns || []
      entityForm.primary_key = schema.primary_keys?.[0] || entityForm.primary_key || 'id'
      entityForm.unique_key =
        schema.indexes?.find((item) => item.unique && item.column_names?.length === 1)
          ?.column_names?.[0] ||
        entityForm.unique_key ||
        ''
      if (
        (!editingId.value || !nameBefore || nameBefore === tableName) &&
        entityForm.name === nameBefore
      )
        entityForm.name =
          schema.table_comment ||
          entityTableOptions.value.find((item) => item.value === tableName)?.comment ||
          tableName
    } catch (loadFailure1) {
      if (request === schemaRequest && current === session && scope.current(version))
        void (reportLoadError(loadFailure1, "表结构加载失败，可重新选择表后重试", false), discoveryError.value = '表结构加载失败，可重新选择表后重试')
    } finally {
      if (request === schemaRequest) schemaLoading.value = false
    }
  }
  function onSchemaChange() {
    resetDiscovery()
  }
  async function saveEntity(): Promise<boolean> {
    if (
      !entityVisible.value ||
      entitySaving.value ||
      entityTableLoading.value ||
      schemaLoading.value ||
      !scope.isActive()
    )
      return false
    const error = validateEntity(entityForm)
    if (error) {
      Message.error(error)
      return false
    }
    const current = session,
      version = scope.snapshot(),
      id = editingId.value,
      payload = entityPayload(entityForm)
    const sync = syncFieldsAfterSave.value,
      environment = userStore.selected_environment
    let savedId: number | null = null
    entitySaving.value = true
    syncError.value = ''
    emit('saving-change', id, true)
    try {
      const response = await (id === null
        ? postDataFactoryEntity(payload)
        : putDataFactoryEntity({ ...payload, id }))
      if (current !== session || !scope.current(version)) return false
      savedId = response.data?.id ?? id
      if (savedId !== null) editingId.value = savedId
      emit('saved')
      if (sync && savedId !== null) {
        if (environment == null) throw Error('sync-environment-missing')
        let columns = entityDiscoveredColumns.value
        if (!columns.length) {
          const schema = await postDataFactoryDiscoverTable({
            datasource_alias_id: payload.datasource_alias,
            project_product: payload.project_product,
            test_env: environment,
            table_name: payload.table_name,
            schema_name: payload.schema_name,
          })
          if (current !== session || !scope.current(version)) return false
          columns = schema.data?.columns || []
        }
        if (!columns.length)
          Message.warning('实体已保存，但没有发现可同步的字段，请进入字段规则手动同步')
        else {
          await postDataFactoryFieldBatchSave({
            entity_id: savedId,
            replace: true,
            fields: columns.map((field, index) => ({
              ...fieldMetadata(field),
              entity: savedId,
              generator_type: field.generator_type ?? field.recommend?.generator_type ?? 1,
              generator_config: field.generator_config ?? field.recommend?.generator_config ?? {},
              sort: index,
            })),
          })
          if (current !== session || !scope.current(version)) return false
          Message.success('实体和字段规则保存成功')
        }
      } else Message.success(response.msg)
      close()
      return true
    } catch (requestFailure) {
      if (savedId !== null && current === session && scope.current(version))
        syncError.value = requestFailureMessage(requestFailure, '实体已保存，字段同步未完成；可重试保存与同步，或关闭后进入字段规则同步。')
      return false
    } finally {
      entitySaving.value = false
      emit('saving-change', id, false)
    }
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-entity-edit-form {
    min-width: 0;
  }

  .mango-entity-form-section + .mango-entity-form-section {
    margin-top: var(--m-card-padding);
    padding-top: var(--m-card-padding);
    border-top: 1px solid var(--m-border);
  }

  .mango-entity-form-title {
    margin: 0 0 var(--m-page-gap);
    color: var(--m-text);
    font-size: var(--m-font-body);
    font-weight: 600;
  }

  .mango-entity-form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
    gap: var(--m-page-gap);
  }

  .mango-entity-form-grid > div {
    min-width: 0;
  }

  .mango-entity-form-full {
    grid-column: 1 / -1;
  }

  .mango-entity-edit-form :deep(.arco-form-item) {
    margin-bottom: 0;
  }

  .mango-entity-edit-form :deep(.arco-form-item-label-col) {
    flex: 0 0 100px;
    width: 100px;
    max-width: none;
    white-space: nowrap;
  }

  .mango-entity-edit-form :deep(.arco-form-item-wrapper-col) {
    flex: 1;
    min-width: 0;
    width: auto;
    max-width: none;
  }

  .mango-entity-status-log-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: var(--m-space-md);
  }

  .mango-entity-table-select-group {
    display: flex;
    width: 100%;
  }

  .mango-entity-table-select {
    flex: 1;
    min-width: 0;
  }

  .mango-entity-table-refresh {
    flex: 0 0 112px;
  }

  .mango-entity-full-width {
    width: 100%;
  }
</style>
