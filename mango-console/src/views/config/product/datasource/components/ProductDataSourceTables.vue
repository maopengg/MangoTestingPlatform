<template>
  <div class="mango-product-tables">
    <div class="mango-product-tables-toolbar">
      <div class="mango-product-tables-field mango-product-tables-field--binding">
        <a-select
          size="small"
          v-model="bindingId"
          :options="bindingOptions"
          :disabled="generating"
          placeholder="选择读取表结构的环境绑定"
          class="mango-product-tables-environment"
          aria-label="环境绑定"
        />
      </div>
      <div class="mango-product-tables-field">
        <a-input
          size="small"
          v-model="keyword"
          placeholder="搜索表名或说明"
          allow-clear
          class="mango-product-tables-search"
          aria-label="搜索表名或说明"
        />
      </div>
      <div v-if="source?.db_type === 1" class="mango-product-tables-field">
        <a-select
          v-model="selectedSchema"
          :options="schemaOptions"
          :loading="schemasLoading"
          class="mango-product-tables-environment"
          size="small"
          allow-search
          allow-create
          allow-clear
          placeholder="选择 Schema"
        />
      </div>
      <a-space v-if="relational" class="mango-product-tables-actions">
        <a-button
          size="small"
          type="primary"
          :disabled="!selectedKeys.length || generating"
          @click="openGenerate"
          >生成工厂实体（{{ selectedKeys.length }}）</a-button
        >
      </a-space>
    </div>
    <template v-if="error"><a-button size="small" :loading="loading" @click="loadTables">重新加载</a-button></template>
    <template v-if="schemasError"><a-button size="small" :loading="schemasLoading" @click="loadSchemaOptions"
        >重新加载</a-button></template>
    <div v-if="!binding" class="mango-empty-state">请先为当前逻辑数据库配置允许读取的环境绑定</div>
    <div v-else-if="!supportsTables" class="mango-empty-state"
      >此类型不提供业务表发现，请使用逻辑数据源的查询能力</div
    >
    <div class="mango-product-tables-grid">
      <a-table
        v-if="binding && supportsTables"
        :columns="visibleColumns"
        :data="pagedTables"
        :loading="loading"
        :pagination="false"
        :scroll="{ x: 700 }"
        row-key="key"
        size="small"
        :bordered="false"
        :row-selection="relational ? rowSelection : undefined"
        @selection-change="selectedKeys = $event.map(String)"
      >
        <template #actions="{ record }"
          ><MangoTableActions :actions="[{ label: '表结构', onClick: () => viewSchema(record) }]"
        /></template>
      </a-table>
      <TableFooter
        v-if="binding && supportsTables"
        :pagination="pagination"
        :show-refresh="false"
      />
    </div>
  </div>
  <a-drawer v-model:visible="schemaVisible" :title="schemaTitle" :width="900" :footer="false">
    
    <a-table
      :columns="schemaColumns"
      :data="schema?.columns || []"
      :loading="schemaLoading"
      row-key="name"
      :pagination="false"
      :scroll="{ x: 850, y: 480 }"
      class="mango-native-scroll-table"
      :bordered="false"
      size="small"
    >
      <template #nullable="{ record }">{{ record.nullable ? '是' : '否' }}</template>
      <template #primary_key="{ record }">{{ record.primary_key ? '是' : '否' }}</template>
      <template #autoincrement="{ record }">{{ record.autoincrement ? '是' : '否' }}</template>
    </a-table>
    <div class="mango-source-results">
      <strong>索引</strong>
      <p v-for="(index, key) in schema?.indexes || []" :key="key"
        >{{ index.name }} · {{ (index.column_names || []).join(', ')
        }}{{ index.unique ? ' · 唯一' : '' }}</p
      >
      <strong>外键</strong>
      <p v-for="(foreign, key) in schema?.foreign_keys || []" :key="key"
        >{{ (foreign.constrained_columns || []).join(', ') }} → {{ foreign.referred_table }}.{{
          (foreign.referred_columns || []).join(', ')
        }}</p
      >
    </div>
  </a-drawer>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="generateVisible"
    title="生成工厂实体"
    :width="560"
    :on-before-ok="generate"
    :ok-loading="generating"
    :closable="!generating"
    :mask-closable="!generating"
    :cancel-button-props="{ disabled: generating }"
    :esc-to-close="!generating"
    ok-text="生成"
  >
    <p
      >所选绑定：{{ environmentName(binding?.environment) }} /
      {{ binding?.database_name || '未选默认库' }}</p
    >
    <a-form auto-label-width class="mango-simple-form" :model="generateForm" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="所属模块" required
        ><ProductModuleSelect
          v-model="generateForm.module"
          :project-product-id="productId"
          :disabled="generating"
      /></a-form-item>
    </a-form>
    <p class="mango-product-tables-description"
      >在当前产品下生成所选表，实体名称使用表注释或表名。跳过已有实体，同步字段规则并执行平台启用校验。</p
    >
    <div v-if="generationResults.length" class="mango-product-tables-results">
      <strong>{{
        generating
          ? '正在生成：' + generationResults.length + ' / ' + generationTotal
          : '生成结果；失败项保留勾选，可修复后再次生成'
      }}</strong>
      <p v-for="item in generationResults" :key="item.table_name"
        >{{ item.table_name }}：{{ item.message }}</p
      >
    </div>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    postDataFactoryDiscoverTables,
    postDataFactoryDiscoverTable,
    postDataFactoryEntityBatchGenerate,
  } from '@/api/data-factory'
  import { getDataSourceSchemas } from '@/api/system/data_source'
  import { useEnum } from '@/store/modules/get-enum'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import { usePagination } from '@/hooks/table'
  import { getOptionId } from '@/utils/business-format'
  import { discoveryColumns, schemaColumns } from '../config'
  import { bindingDataSource, requestError } from '../form'
  import { useProductDatasourceScope } from '../composables/useProductDatasourceScope'
  import type {
    EntityId,
    LogicalBinding,
    DiscoveredTable,
    TableSchema,
    GenerationResult,
  } from '../types'
  const props = defineProps<{
    aliasId: EntityId
    productId: EntityId
    bindings: LogicalBinding[]
  }>()
  const enums = useEnum()
  const bindingId = ref<number | null>(null)
  const binding = computed(() => props.bindings.find((item) => item.id === bindingId.value))
  const source = computed(() => (binding.value ? bindingDataSource(binding.value) : null))
  const selectedSchema = ref(''),
    schemaOptions = ref<string[]>([]),
    schemasLoading = ref(false),
    schemasError = ref('')
  const relational = computed(() => source.value?.source_category === 0)
  const supportsTables = computed(() => relational.value || source.value?.db_type === 20)
  const bindingOptions = computed(() =>
    props.bindings.map((item) => ({
      value: item.id,
      label:
        environmentName(item.environment) +
        ' / ' +
        (bindingDataSource(item)?.display_name || bindingDataSource(item)?.name || '') +
        (item.db_c_status === 1 ? '' : '（禁止读取）'),
      disabled: item.db_c_status !== 1 || item.environment === null,
    }))
  )
  const keyword = ref(''),
    tables = ref<DiscoveredTable[]>([]),
    loading = ref(false),
    error = ref(''),
    selectedKeys = ref<string[]>([])
  const schema = ref<TableSchema | null>(null),
    schemaVisible = ref(false),
    schemaTitle = ref(''),
    schemaLoading = ref(false),
    schemaError = ref('')
  const generateVisible = ref(false),
    generating = ref(false),
    generateForm = reactive<{ module: EntityId | EntityId[] | null }>({ module: null })
  const generationResults = ref<GenerationResult[]>([]),
    generationTotal = ref(0)
  let version = 0,
    schemaVersion = 0,
    schemaOptionsVersion = 0
  const visibleColumns = computed(() =>
    relational.value ? discoveryColumns : discoveryColumns.filter((item) => !item.slotName)
  )
  const filteredTables = computed(() =>
    tables.value.filter((item) =>
      (item.name + ' ' + (item.comment || '')).toLowerCase().includes(keyword.value.toLowerCase())
    )
  )
  const pagination = usePagination(() => undefined, ref(false))
  const pagedTables = computed(() =>
    filteredTables.value.slice(
      (pagination.page - 1) * pagination.pageSize,
      pagination.page * pagination.pageSize
    )
  )
  watch(
    () => filteredTables.value.length,
    (total) => {
      pagination.setTotalSize(total)
      pagination.page = Math.min(
        pagination.page,
        Math.max(1, Math.ceil(total / pagination.pageSize))
      )
    },
    { immediate: true }
  )
  watch(keyword, () => {
    pagination.page = 1
  })
  const rowSelection = computed(() => ({
    type: 'checkbox' as const,
    selectedRowKeys: selectedKeys.value,
    showCheckedAll: true,
    getCheckboxProps: () => ({ disabled: generating.value }),
  }))
  const scope = useProductDatasourceScope(
    () => [],
    resetAll,
    () => {
      void loadSchemaOptions()
      void loadTables()
    }
  )
  function environmentName(value: number | null | undefined) {
    return (
      enums.environment_type?.find((item) => Number(item.key) === value)?.title ||
      String(value ?? '未配置')
    )
  }
  function params() {
    return {
      datasource_alias_id: Number(props.aliasId),
      project_product: Number(props.productId),
      test_env: binding.value?.environment,
      schema_name: selectedSchema.value,
    }
  }
  function contextKey() {
    return JSON.stringify([props.aliasId, props.productId, binding.value, selectedSchema.value])
  }
  function resetView() {
    ++version
    ++schemaVersion
    tables.value = []
    selectedKeys.value = []
    keyword.value = ''
    error.value = ''
    loading.value = false
    schema.value = null
    schemaLoading.value = false
    schemaError.value = ''
    schemaVisible.value = false
    generateVisible.value = false
    generationResults.value = []
    generateForm.module = null
    pagination.page = 1
  }
  function resetAll() {
    resetView()
    ++schemaOptionsVersion
    schemaOptions.value = []
    schemasLoading.value = false
    schemasError.value = ''
  }
  watch(
    () => [
      props.aliasId,
      props.productId,
      ...props.bindings.map((item) => `${item.id}:${item.db_c_status}:${item.environment}`),
    ],
    () => {
      if (
        !props.bindings.some(
          (item) =>
            item.id === bindingId.value && item.db_c_status === 1 && item.environment !== null
        )
      )
        bindingId.value =
          props.bindings.find((item) => item.db_c_status === 1 && item.environment !== null)?.id ??
          null
    },
    { immediate: true, flush: 'sync' }
  )
  watch(
    binding,
    () => {
      selectedSchema.value = binding.value?.schema_name || ''
      void loadSchemaOptions()
    },
    { immediate: true }
  )
  watch(
    contextKey,
    () => {
      resetView()
      void loadTables()
    },
    { immediate: true }
  )
  watch(
    schemaVisible,
    (visible) => {
      if (!visible) {
        ++schemaVersion
        schemaLoading.value = false
        schema.value = null
      }
    },
    { flush: 'sync' }
  )
  async function loadSchemaOptions() {
    const current = ++schemaOptionsVersion,
      id = source.value?.id,
      database = binding.value?.database_name,
      token = scope.snapshot()
    schemaOptions.value = []
    schemasLoading.value = false
    schemasError.value = ''
    if (!scope.isActive() || id == null || !database || source.value?.db_type !== 1) return
    schemasLoading.value = true
    try {
      const res = await getDataSourceSchemas({ data_source_id: id, database_name: database })
      if (current === schemaOptionsVersion && scope.current(token))
        schemaOptions.value = (res.data || []).map((item: { name: string } | string) =>
          typeof item === 'string' ? item : item.name
        )
    } catch (failure: unknown) {
      if (current === schemaOptionsVersion && scope.current(token))
        void (reportLoadError(failure, "加载失败，请重试", false), schemasError.value = requestError(failure))
    } finally {
      if (current === schemaOptionsVersion) schemasLoading.value = false
    }
  }
  async function loadTables() {
    if (
      !scope.isActive() ||
      !binding.value ||
      binding.value.db_c_status !== 1 ||
      !supportsTables.value ||
      loading.value
    )
      return
    const current = version,
      token = scope.snapshot(),
      key = contextKey(),
      payload = { ...params(), refresh: false }
    loading.value = true
    error.value = ''
    try {
      const res = await postDataFactoryDiscoverTables(payload)
      if (current === version && scope.current(token) && key === contextKey()) {
        tables.value = (res.data || []).map((item: Omit<DiscoveredTable, 'key'> | string) => {
          const row = typeof item === 'string' ? { name: item, comment: '' } : item
          return { ...row, key: JSON.stringify([row.schema_name || '', row.name]) }
        })
        selectedKeys.value = []
      }
    } catch (failure: unknown) {
      if (current === version && scope.current(token) && key === contextKey())
        void (reportLoadError(failure, "加载失败，请重试", false), error.value = requestError(failure))
    } finally {
      if (current === version) loading.value = false
    }
  }
  async function viewSchema(row: DiscoveredTable) {
    if (!scope.isActive() || !binding.value) return
    const current = version,
      currentSchema = ++schemaVersion,
      token = scope.snapshot(),
      key = contextKey(),
      payload = { ...params(), table_name: row.name }
    schemaVisible.value = true
    schemaTitle.value = row.name + ' · 表结构'
    schemaLoading.value = true
    schema.value = null
    schemaError.value = ''
    try {
      const res = await postDataFactoryDiscoverTable(payload)
      if (
        current === version &&
        currentSchema === schemaVersion &&
        scope.current(token) &&
        key === contextKey()
      )
        schema.value = res.data
    } catch (failure: unknown) {
      if (
        current === version &&
        currentSchema === schemaVersion &&
        scope.current(token) &&
        key === contextKey()
      )
        void (reportLoadError(failure, "加载失败，请重试", false), schemaError.value = requestError(failure))
    } finally {
      if (current === version && currentSchema === schemaVersion) schemaLoading.value = false
    }
  }
  function openGenerate() {
    if (!scope.isActive() || generating.value) return
    generateVisible.value = true
    generationResults.value = []
    generateForm.module = null
  }
  async function generate(): Promise<boolean> {
    if (generating.value || !scope.isActive() || !generateVisible.value) return false
    const moduleId: unknown = getOptionId(generateForm.module)
    if (
      (typeof moduleId !== 'number' && typeof moduleId !== 'string') ||
      moduleId === '' ||
      !binding.value ||
      !selectedKeys.value.length
    ) {
      Message.warning('请选择模块和数据表')
      return false
    }
    const current = version,
      token = scope.snapshot(),
      key = contextKey(),
      schemaName = selectedSchema.value
    const requested = tables.value
      .filter((item) => selectedKeys.value.includes(item.key))
      .map((item) => ({
        table_name: item.name,
        schema_name: item.schema_name || schemaName,
        name: String(item.comment || item.name).slice(0, 64),
      }))
    const payload = {
      project_product: Number(props.productId),
      datasource_alias: Number(props.aliasId),
      test_env: binding.value.environment,
      module: moduleId,
      sync_fields: true,
      skip_exists: true,
    }
    generating.value = true
    generationTotal.value = requested.length
    generationResults.value = []
    const valid = () => current === version && scope.current(token) && key === contextKey()
    try {
      for (let offset = 0; offset < requested.length && valid(); offset += 5) {
        const batch = requested.slice(offset, offset + 5)
        try {
          const res = await postDataFactoryEntityBatchGenerate({ ...payload, tables: batch })
          if (valid()) generationResults.value.push(...(res.data?.items || []))
        } catch (failure: unknown) {
          if (valid())
            generationResults.value.push(
              ...batch.map((item) => ({
                table_name: item.table_name,
                status: 'failed',
                message: requestError(failure),
              }))
            )
        }
      }
      if (valid()) {
        selectedKeys.value = generationResults.value
          .filter((item) => !['success', 'skipped'].includes(item.status))
          .flatMap((item) => {
            const row = tables.value.find((row) => row.name === item.table_name)
            return row ? [row.key] : []
          })
        if (selectedKeys.value.length) Message.warning('部分表失败，可查看原因后重试')
        else Message.success('所选表已完成生成或已存在')
      }
      return false
    } finally {
      generating.value = false
    }
  }
</script>
<style scoped>
  .mango-product-tables {
    margin-top: var(--m-page-gap);
    min-width: 0;
  }
  .mango-product-tables-toolbar {
    display: flex;
    align-items: center;
    flex-wrap: nowrap;
    gap: var(--m-page-gap);
    padding: var(--m-page-gap);
    margin-bottom: var(--m-page-gap);
    background: var(--m-bg);
    border-radius: var(--m-radius-sm);
  }
  .mango-product-tables-field {
    flex: 0 0 var(--table-filter-control-width, 160px);
    min-width: 0;
    width: var(--table-filter-control-width, 160px);
    max-width: 100%;
  }
  .mango-product-tables-field :deep(.arco-select-view),
  .mango-product-tables-field :deep(.arco-input-wrapper) {
    width: 100%;
  }
  .mango-product-tables-field--binding {
    flex-basis: calc(var(--table-filter-control-width, 160px) * 2);
    width: calc(var(--table-filter-control-width, 160px) * 2);
  }
  .mango-product-tables-actions {
    flex: 0 0 auto;
    margin-left: auto;
  }
  .mango-product-tables-grid {
    min-width: 0;
  }
  .mango-product-tables-description {
    color: var(--m-muted);
    font-size: var(--m-font-caption);
  }
  .mango-product-tables-results,
  .mango-source-results {
    margin-top: var(--m-page-gap);
    padding: 12px;
    background: var(--m-bg);
    border-radius: var(--m-radius-sm);
    overflow-wrap: anywhere;
  }
</style>
