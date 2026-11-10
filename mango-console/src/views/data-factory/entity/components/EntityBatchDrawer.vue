<template>
  <BaseSidePanel
    :visible="batchVisible"
    title="批量生成数据实体"
    :width="1000"
    :mask-closable="!batchGenerating"
    @update:visible="
      (value) => {
        if (!value) close()
      }
    "
  >
    <a-alert v-if="generateError" type="error"
      >生成请求未确认，请重新加载表核对已存在实体后再重试</a-alert
    >
    <a-form :disabled="batchGenerating" :model="batchForm" layout="horizontal">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="产品" required>
            <ProjectProductSelect
              v-model="batchForm.project_product"
              :disabled="batchGenerating"
              @change="onBatchProjectChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="模块名称" required>
            <ProductModuleSelect
              v-model="batchForm.module"
              :disabled="batchGenerating"
              :project-product-id="batchForm.project_product"
              :auto-clear="false"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="逻辑数据库" required>
            <a-select
              v-model="batchForm.datasource_alias"
              :field-names="{ value: 'id', label: 'name' }"
              :options="datasourceAliasOptions"
              :loading="aliasLoading"
              allow-clear
              allow-search
            />
          </a-form-item>
        </a-grid-item>
      </a-grid>
      <a-space class="mango-entity-toolbar">
        <a-switch
          v-model="batchForm.sync_fields"
          checked-text="同步字段规则"
          unchecked-text="不同步字段"
        />
        <a-switch
          v-model="batchForm.skip_exists"
          checked-text="跳过已存在"
          unchecked-text="已存在报错"
        />
        <a-button
          :loading="batchLoading"
          :disabled="batchGenerating"
          type="primary"
          @click="loadBatchTables"
          data-testid="qa-views-data-factory-entity-button-加载表"
          >加载表</a-button
        >
        <a-button
          :loading="batchGenerating"
          status="success"
          @click="batchGenerateEntities"
          data-testid="qa-views-data-factory-entity-button-生成"
          >生成</a-button
        >
      </a-space>
    </a-form>
    <a-alert class="mango-entity-alert" type="info">
      当前使用顶部全局测试环境读取表结构。实体名称默认使用表注释，没有表注释时使用表名。
    </a-alert>
    <a-table
      class="mango-native-scroll-table"
      :columns="batchEntityTableColumns"
      :data="batchRows"
      :loading="batchLoading || batchGenerating"
      :pagination="false"
      row-key="key"
      :row-selection="batchRowSelection"
      :scroll="{ x: 900, y: 520 }"
      @selection-change="onBatchSelectionChange"
    >
      <template #columns>
        <a-table-column
          v-for="item of batchEntityTableColumns"
          :key="item.key"
          :align="item.align"
          :data-index="item.key"
          :ellipsis="item.ellipsis"
          :tooltip="item.tooltip"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'name'" #cell="{ record }">
            <a-input v-model="record.name" :disabled="record.disabled || batchGenerating" />
          </template>
          <template v-else-if="item.key === 'status'" #cell="{ record }">
            <a-tag :color="getBatchStatusColor(record.status)">{{
              getBatchStatusText(record.status)
            }}</a-tag>
          </template>
        </a-table-column>
      </template>
    </a-table>
    <template #footer-buttons>
      <a-space>
        <a-button
          :disabled="batchGenerating"
          @click="close"
          data-testid="qa-views-data-factory-entity-button-关闭"
          >关闭</a-button
        >
        <a-button
          :loading="batchLoading"
          :disabled="batchGenerating"
          @click="loadBatchTables"
          data-testid="qa-views-data-factory-entity-button-重新加载"
          >重新加载</a-button
        >
        <a-button
          :loading="batchGenerating"
          status="success"
          type="primary"
          @click="batchGenerateEntities"
          data-testid="qa-views-data-factory-entity-button-确认生成"
        >
          确认生成
        </a-button>
      </a-space>
    </template>
  </BaseSidePanel>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    getDataFactoryEntity,
    postDataFactoryDiscoverTables,
    postDataFactoryEntityBatchGenerate,
  } from '@/api/data-factory'
  import useUserStore from '@/store/modules/user'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import { batchEntityTableColumns } from '../config'
  import { createBatchDraft, optionId, normalizeTable, tableKey } from '../form'
  import { useEntityScope } from '../composables/useEntityScope'
  import { useEntityAliases } from '../composables/useEntityAliases'
  import type { NavigationDefaults, BatchRow, TableInfo, EntityRecord, BatchResult } from '../types'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const userStore = useUserStore(),
    aliases = useEntityAliases()
  const { options: datasourceAliasOptions, loading: aliasLoading, error: aliasError } = aliases
  const batchVisible = ref(false),
    batchLoading = ref(false),
    batchGenerating = ref(false),
    loadError = ref(false),
    generateError = ref(false)
  const batchForm = reactive(createBatchDraft()),
    batchRows = ref<BatchRow[]>([]),
    batchSelectedKeys = ref<string[]>([])
  const batchRowSelection = computed(() => ({
    selectedRowKeys: batchSelectedKeys.value,
    showCheckedAll: true,
    getCheckboxProps: (row: BatchRow) => ({ disabled: row.disabled || batchGenerating.value }),
  }))
  let session = 0,
    request = 0
  const scope = useEntityScope(close)
  watch(
    () => [batchForm.project_product, batchForm.module, batchForm.datasource_alias],
    () => {
      ++request
      batchRows.value = []
      batchSelectedKeys.value = []
      batchLoading.value = false
      loadError.value = false
    },
    { flush: 'sync' }
  )
  function open(defaults?: NavigationDefaults) {
    if (!scope.isActive() || batchGenerating.value) return
    close()
    Object.assign(batchForm, createBatchDraft(defaults))
    batchVisible.value = true
    void aliases.load(batchForm.project_product)
  }
  function close() {
    ++session
    ++request
    batchVisible.value = false
    batchRows.value = []
    batchSelectedKeys.value = []
    batchLoading.value = false
    loadError.value = false
    generateError.value = false
    aliases.clear()
    Object.assign(batchForm, createBatchDraft())
  }
  function onBatchProjectChange(value: unknown) {
    if (batchGenerating.value) return
    batchForm.project_product = optionId(value)
    batchForm.module = null
    batchForm.datasource_alias = null
    void aliases.load(value)
  }
  function validate(): boolean {
    if (optionId(batchForm.project_product) === null) {
      Message.error('请选择产品')
      return false
    }
    if (optionId(batchForm.module) === null) {
      Message.error('请选择模块名称')
      return false
    }
    if (optionId(batchForm.datasource_alias) === null) {
      Message.error('请选择逻辑数据库')
      return false
    }
    if (userStore.selected_environment == null) {
      Message.error('请先在顶部选择测试环境')
      return false
    }
    return true
  }
  async function loadBatchTables() {
    if (!batchVisible.value || batchGenerating.value || !scope.isActive() || !validate()) return
    const current = ++request,
      version = scope.snapshot(),
      payload = {
        project_product: optionId(batchForm.project_product),
        module: optionId(batchForm.module),
        datasource_alias: optionId(batchForm.datasource_alias),
      }
    batchLoading.value = true
    loadError.value = false
    try {
      const [tableResponse, entities] = await Promise.all([
        postDataFactoryDiscoverTables({
          datasource_alias_id: payload.datasource_alias,
          project_product: payload.project_product,
          test_env: userStore.selected_environment,
        }),
        getDataFactoryEntity({ ...payload, page: 1, pageSize: 9999 }),
      ])
      if (current !== request || !scope.current(version)) return
      const exists = new Map<string, EntityRecord>(
        (entities.data || []).map((entity: EntityRecord) => [
          tableKey(entity.schema_name || '', entity.table_name),
          entity,
        ])
      )
      batchRows.value = (tableResponse.data || []).map((value: string | TableInfo) => {
        const table = normalizeTable(value),
          key = tableKey(table.schema_name, table.value),
          entity = exists.get(key)
        return {
          key,
          table_name: table.value,
          schema_name: table.schema_name,
          table_comment: table.comment,
          name: entity?.name || table.comment || table.value,
          status: entity ? 'exists' : 'ready',
          message: entity ? `已存在实体：${entity.name}` : '可生成',
          disabled: Boolean(entity),
        }
      })
      batchSelectedKeys.value = batchRows.value.filter((row) => !row.disabled).map((row) => row.key)
      Message.success('表加载完成')
    } catch (loadFailure0) {
      if (current === request && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (current === request) batchLoading.value = false
    }
  }
  function onBatchSelectionChange(keys: Array<string | number>) {
    if (!batchGenerating.value)
      batchSelectedKeys.value = batchRows.value
        .filter((row) => !row.disabled && keys.includes(row.key))
        .map((row) => row.key)
  }
  async function batchGenerateEntities() {
    if (
      !batchVisible.value ||
      batchGenerating.value ||
      batchLoading.value ||
      !scope.isActive() ||
      !validate()
    )
      return
    const selected = batchRows.value
      .filter((row) => !row.disabled && batchSelectedKeys.value.includes(row.key))
      .map((row) => ({ ...row }))
    if (!selected.length) {
      Message.error('请至少选择一张可生成的表')
      return
    }
    const empty = selected.find((row) => !row.name)
    if (empty) {
      Message.error(`表 ${empty.table_name} 的实体名称不能为空`)
      return
    }
    const current = session,
      version = scope.snapshot(),
      payload = {
        project_product: optionId(batchForm.project_product),
        module: optionId(batchForm.module),
        datasource_alias: optionId(batchForm.datasource_alias),
        test_env: userStore.selected_environment,
        sync_fields: batchForm.sync_fields,
        skip_exists: batchForm.skip_exists,
        tables: selected.map((row) => ({
          table_name: row.table_name,
          schema_name: row.schema_name,
          name: row.name,
        })),
      }
    batchGenerating.value = true
    generateError.value = false
    try {
      const response = await postDataFactoryEntityBatchGenerate(payload)
      if (current !== session || !scope.current(version)) return
      const result: BatchResult = response.data || { items: [] },
        queues = new Map<string, BatchResult['items']>()
      for (const item of result.items || [])
        queues.set(item.table_name, [...(queues.get(item.table_name) || []), item])
      const mapped = new Map(selected.map((row) => [row.key, queues.get(row.table_name)?.shift()]))
      batchRows.value = batchRows.value.map((row) => {
        const item = mapped.get(row.key)
        return item
          ? { ...row, ...item, disabled: item.status === 'success' || item.status === 'skipped' }
          : row
      })
      batchSelectedKeys.value = batchRows.value
        .filter((row) => !row.disabled && batchSelectedKeys.value.includes(row.key))
        .map((row) => row.key)
      Message.success(
        `生成完成：成功 ${result.success || 0}，跳过 ${result.skipped || 0}，失败 ${
          result.failed || 0
        }`
      )
      emit('saved')
      if (!result.failed) close()
    } catch {
      if (current === session && scope.current(version)) generateError.value = true
    } finally {
      batchGenerating.value = false
    }
  }
  const getBatchStatusText = (status: string) =>
    ({ ready: '可生成', exists: '已存在', success: '成功', skipped: '跳过', failed: '失败' }[
      status
    ] ||
    status ||
    '-')
  const getBatchStatusColor = (status: string) =>
    ({ ready: 'arcoblue', exists: 'gray', success: 'green', skipped: 'orange', failed: 'red' }[
      status
    ] || 'gray')
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-entity-toolbar,
  .mango-entity-alert {
    margin-bottom: var(--m-page-gap);
  }
</style>
