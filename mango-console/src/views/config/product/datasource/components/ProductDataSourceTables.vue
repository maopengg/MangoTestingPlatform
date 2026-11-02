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
      <a-select v-model="selectedSchema" :options="schemaOptions" :loading="schemasLoading"
        class="mango-product-tables-environment" size="small" allow-search allow-create allow-clear placeholder="选择 Schema" />
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
    <a-alert v-if="error" type="error">{{ error }}</a-alert>
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
      @selection-change="selectedKeys = $event"
    >
      <template #actions="{ record }"
        ><MangoTableActions :actions="[{ label: '表结构', onClick: () => viewSchema(record) }]"
      /></template>
    </a-table>
    <TableFooter v-if="binding && supportsTables" :pagination="pagination" :show-refresh="false" />
    </div>
  </div>
  <a-drawer v-model:visible="schemaVisible" :title="schemaTitle" :width="900" :footer="false">
    <a-alert v-if="schemaError" type="error">{{ schemaError }}</a-alert>
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
    v-model:visible="generateVisible"
    title="生成工厂实体"
    :width="720"
    :on-before-ok="generate"
    :ok-loading="generating"
    :closable="!generating"
    :mask-closable="!generating"
    :cancel-button-props="{ disabled: generating }"
    ok-text="生成"
  >
    <p>所选绑定：{{ environmentName(binding?.environment) }} / {{ binding?.database_name || '未选默认库' }}</p>
    <a-form :model="generateForm" layout="horizontal">
      <a-form-item label="所属模块" required
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
  import { computed, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    postDataFactoryDiscoverTables,
    postDataFactoryDiscoverTable,
    postDataFactoryEntityBatchGenerate,
  } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import { usePagination } from '@/hooks/table'
  import { discoveryColumns, schemaColumns } from '../config'
  import { getDataSourceSchemas } from '@/api/system/data_source'
  const props = defineProps<{
    aliasId: string | number
    productId: string | number
    bindings: any[]
  }>()
  const enums = useEnum()
  const bindingId = ref<number>()
  const binding = computed(() => props.bindings.find((item) => item.id === bindingId.value))
  const source = computed(() => binding.value?.data_source || binding.value?.database)
  const selectedSchema = ref('')
  const schemaOptions = ref<string[]>([])
  const schemasLoading = ref(false)
  watch(binding, async (value) => {
    selectedSchema.value = value?.schema_name || ''
    schemaOptions.value = []
    if (!value?.database_name || source.value?.db_type !== 1) return
    schemasLoading.value = true
    try {
      const res = await getDataSourceSchemas({ data_source_id: source.value.id, database_name: value.database_name })
      if (binding.value?.id === value.id) schemaOptions.value = (res.data || []).map((item: any) => item.name)
    } finally { schemasLoading.value = false }
  }, { immediate: true })
  const relational = computed(() => source.value?.source_category === 0)
  const supportsTables = computed(() => relational.value || source.value?.db_type === 20)
  const bindingOptions = computed(() =>
    props.bindings.map((item) => ({
      value: item.id,
      label:
        environmentName(item.environment) +
        ' / ' +
        ((item.data_source || item.database)?.display_name ||
          (item.data_source || item.database)?.name ||
          '') +
        (item.db_c_status === 1 ? '' : '（禁止读取）'),
      disabled: item.db_c_status !== 1 || item.environment == null,
    }))
  )
  const keyword = ref('')
  const tables = ref<any[]>([])
  const loading = ref(false)
  const error = ref('')
  const selectedKeys = ref<any[]>([])
  const schema = ref<any>()
  const schemaVisible = ref(false)
  const schemaTitle = ref('')
  const schemaLoading = ref(false)
  const schemaError = ref('')
  const generateVisible = ref(false)
  const generating = ref(false)
  const generateForm = reactive<{ module?: any }>({})
  const generationResults = ref<any[]>([])
  const generationTotal = ref(0)
  let version = 0
  let schemaVersion = 0
  const visibleColumns = computed(() =>
    relational.value ? discoveryColumns : discoveryColumns.filter((item) => !item.slotName)
  )
  const filteredTables = computed(() =>
    tables.value.filter((item) =>
      (item.name + ' ' + (item.comment || '')).toLowerCase().includes(keyword.value.toLowerCase())
    )
  )
  const pagination = usePagination(() => undefined, ref(false))
  const pagedTables = computed(() => {
    const start = (pagination.page - 1) * pagination.pageSize
    return filteredTables.value.slice(start, start + pagination.pageSize)
  })
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
  function environmentName(value: any) {
    return (
      enums.environment_type?.find((item: any) => item.key === value)?.title ||
      String(value ?? '未配置')
    )
  }
  function errorText(value: any) {
    return value?.message || value?.msg || '请求未确认，请刷新后重试'
  }
  function params() {
    return {
      datasource_alias_id: Number(props.aliasId),
      project_product: Number(props.productId),
      test_env: binding.value?.environment,
      schema_name: selectedSchema.value,
    }
  }
  watch(
    () => [props.aliasId, ...props.bindings.map((item) => item.id + ':' + item.db_c_status)],
    () => {
      if (!props.bindings.some((item) => item.id === bindingId.value && item.db_c_status === 1))
        bindingId.value = props.bindings.find(
          (item) => item.db_c_status === 1 && item.environment != null
        )?.id
    },
    { immediate: true }
  )
  watch(
    [
      () => props.aliasId,
      bindingId,
      selectedSchema,
      () => source.value?.id,
      () => source.value?.update_time,
      () => binding.value?.db_c_status,
    ],
    () => {
      version++
      pagination.page = 1
      schemaVersion++
      tables.value = []
      selectedKeys.value = []
      keyword.value = ''
      error.value = ''
      loading.value = false
      schemaLoading.value = false
      schemaVisible.value = false
      generateVisible.value = false
      generationResults.value = []
      generateForm.module = undefined
      loadTables()
    },
    { immediate: true }
  )
  async function loadTables() {
    if (!binding.value || binding.value.db_c_status !== 1 || !supportsTables.value || loading.value)
      return
    const current = version
    loading.value = true
    error.value = ''
    try {
      const res = await postDataFactoryDiscoverTables({ ...params(), refresh: false })
      if (current === version) {
        tables.value = (res.data || []).map((item: any) => {
          const row = typeof item === 'string' ? { name: item, comment: '' } : item
          return { ...row, key: JSON.stringify([row.schema_name || '', row.name]) }
        })
        selectedKeys.value = []
      }
    } catch (failure) {
      if (current === version) error.value = errorText(failure)
    } finally {
      if (current === version) loading.value = false
    }
  }
  async function viewSchema(row: any) {
    const current = version
    const currentSchema = ++schemaVersion
    schemaVisible.value = true
    schemaTitle.value = row.name + ' · 表结构'
    schemaLoading.value = true
    schema.value = undefined
    schemaError.value = ''
    try {
      const res = await postDataFactoryDiscoverTable({ ...params(), table_name: row.name })
      if (current === version && currentSchema === schemaVersion) schema.value = res.data
    } catch (failure) {
      if (current === version && currentSchema === schemaVersion)
        schemaError.value = errorText(failure)
    } finally {
      if (current === version && currentSchema === schemaVersion) schemaLoading.value = false
    }
  }
  function openGenerate() {
    generateVisible.value = true
    generationResults.value = []
    generateForm.module = undefined
  }
  async function generate() {
    if (!generateForm.module || !binding.value || !selectedKeys.value.length) {
      Message.warning('请选择模块和数据表')
      return false
    }
    const current = version
    const requested = tables.value.filter((item) => selectedKeys.value.includes(item.key))
    const payload = {
      project_product: Number(props.productId),
      datasource_alias: Number(props.aliasId),
      test_env: binding.value.environment,
      module: Array.isArray(generateForm.module)
        ? generateForm.module[generateForm.module.length - 1]
        : generateForm.module,
      sync_fields: true,
      skip_exists: true,
    }
    generating.value = true
    generationTotal.value = requested.length
    generationResults.value = []
    try {
      for (let offset = 0; offset < requested.length && current === version; offset += 5) {
        const batch = requested.slice(offset, offset + 5)
        try {
          const res = await postDataFactoryEntityBatchGenerate({
            ...payload,
            tables: batch.map((item) => ({
              table_name: item.name,
              schema_name: item.schema_name || selectedSchema.value,
              name: String(item.comment || item.name).slice(0, 64),
            })),
          })
          if (current === version) generationResults.value.push(...(res.data?.items || []))
        } catch (failure) {
          if (current === version)
            generationResults.value.push(
              ...batch.map((item) => ({
                table_name: item.name,
                status: 'failed',
                message: errorText(failure),
              }))
            )
        }
      }
      if (current === version) {
        selectedKeys.value = generationResults.value
          .filter((item) => !['success', 'skipped'].includes(item.status))
          .map((item) => tables.value.find(row => row.name === item.table_name)?.key)
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
