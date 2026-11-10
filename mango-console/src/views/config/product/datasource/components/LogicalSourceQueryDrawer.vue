<template>
  <a-drawer v-model:visible="queryDrawer.visible" :width="'50%'" :footer="false" unmount-on-close>
    <template #title> {{ queryDrawerTitle }} / {{ selected?.name || '-' }} </template>
    <div class="mango-sql-query-drawer">
      <div class="mango-sql-query-editor">
        <div v-if="selected?.db_type === 20" class="mango-sql-query-meta">
          <span class="mango-sql-query-label">索引名称</span>
          <a-input
            v-model="queryDrawer.index"
            :disabled="queryDrawer.loading"
            allow-clear
            placeholder="请输入索引名称，例如：order-*"
            data-testid="qa-views-config-product-datasource-input-请输入索引名称-例如-order"
          />
        </div>
        <div class="mango-datasource-query-field">
          <span class="mango-sql-query-label">{{ queryStatementLabel }}</span>
          <a-textarea
            v-model="queryDrawer.statement"
            :disabled="queryDrawer.loading"
            :auto-size="{ minRows: 6, maxRows: 12 }"
            :placeholder="queryStatementPlaceholder"
          />
        </div>
        <div class="mango-sql-query-meta">
          <span class="mango-sql-query-label">测试环境</span>
          <a-select
            v-model="queryDrawer.testEnv"
            :disabled="queryDrawer.loading"
            :field-names="fieldNames"
            :options="enumStore.environment_type"
            allow-clear
            allow-search
            placeholder="请选择测试环境"
            value-key="key"
            data-testid="qa-views-config-product-datasource-select-请选择测试环境"
          />
        </div>
        <div class="mango-sql-query-actions">
          <a-button
            size="small"
            :disabled="queryDrawer.loading"
            @click="resetQueryInput"
            data-testid="qa-views-config-product-datasource-button-清空"
            >清空</a-button
          >
          <a-button
            size="small"
            type="primary"
            :loading="queryDrawer.loading"
            @click="onQueryDatasource"
            data-testid="qa-views-config-product-datasource-button-查询"
          >
            查询
          </a-button>
        </div>
      </div>
      <div class="mango-sql-query-result">
        <div class="mango-sql-query-summary">
          <span>查询结果</span>
          <span class="mango-muted-text">结构化 JSON</span>
        </div>
        <MangoPanelSpin class="mango-datasource-query-loading" :loading="queryDrawer.loading">
          <JsonDisplay
            v-if="queryDrawer.result !== null"
            :data="queryDrawer.result"
            :default-expanded="false"
            :show-drawer-button="false"
          />
          <div v-else class="mango-empty-state">执行查询后将在这里展示结果</div>
        </MangoPanelSpin>
      </div>
    </div>
  </a-drawer>
</template>
<script setup lang="ts">
  import { computed, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postDataSourceExecution, queryLogicalDataSource } from '@/api/data-source-execution'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { fieldNames } from '@/setting'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { useProductDatasourceScope } from '../composables/useProductDatasourceScope'
  import { requestError } from '../form'
  import { queryCopy } from '../config'
  import type { EntityId, LogicalSource } from '../types'
  const props = defineProps<{ productId: EntityId | null; aliasId: number | null }>()
  const enumStore = useEnum(),
    userStore = useUserStore()
  const selected = ref<LogicalSource | null>(null)
  const queryDrawer = reactive({
    visible: false,
    loading: false,
    testEnv: null as number | null,
    index: '',
    statement: '',
    result: null as unknown,
  })
  let request = 0
  const scope = useProductDatasourceScope(() => [props.productId, props.aliasId], close)
  const copy = computed(() => queryCopy[selected.value?.db_type ?? -1] ?? queryCopy.default)
  const queryDrawerTitle = computed(() => copy.value.title)
  const queryStatementLabel = computed(() => copy.value.label)
  const queryStatementPlaceholder = computed(() => copy.value.placeholder)
  function open(record: LogicalSource) {
    if (!scope.isActive() || props.productId === null) return
    ++request
    selected.value = { ...record }
    Object.assign(queryDrawer, {
      visible: true,
      loading: false,
      testEnv: userStore.selected_environment ?? null,
      index: '',
      statement:
        record.db_type === 20 ? '{\n  "query": {\n    "match_all": {}\n  },\n  "size": 20\n}' : '',
      result: null,
    })
  }
  function close() {
    ++request
    queryDrawer.visible = false
    queryDrawer.loading = false
    queryDrawer.result = null
    selected.value = null
  }
  function resetQueryInput() {
    if (queryDrawer.loading) return
    ++request
    queryDrawer.index = ''
    queryDrawer.statement = ''
    queryDrawer.result = null
  }
  watch(
    () => queryDrawer.testEnv,
    () => {
      ++request
      queryDrawer.result = null
      queryDrawer.loading = false
    },
    { flush: 'sync' }
  )
  watch(
    () => queryDrawer.visible,
    (visible) => {
      if (!visible) close()
    },
    { flush: 'sync' }
  )
  async function onQueryDatasource() {
    if (
      queryDrawer.loading ||
      !queryDrawer.visible ||
      !selected.value ||
      props.productId === null ||
      !scope.isActive()
    )
      return
    const statement = queryDrawer.statement.trim(),
      type = selected.value.db_type
    if (!statement) {
      Message.error(`请输入${queryStatementLabel.value}`)
      return
    }
    if (queryDrawer.testEnv == null) {
      Message.error('请选择测试环境')
      return
    }
    let operation_config: string | Record<string, unknown> = statement
    if (type === 20) {
      if (!queryDrawer.index.trim()) {
        Message.error('请输入索引名称')
        return
      }
      let query: unknown
      try {
        query = JSON.parse(statement)
      } catch {
        Message.error('Query DSL 必须是合法的JSON对象')
        return
      }
      if (!query || Array.isArray(query) || typeof query !== 'object') {
        Message.error('Query DSL 必须是JSON对象')
        return
      }
      operation_config = { index: queryDrawer.index.trim(), query }
    }
    const current = ++request,
      version = scope.snapshot(),
      relational = [0, 1, 2].includes(type),
      target = {
        datasource_alias_id: selected.value.id,
        project_product_id: props.productId,
        test_env: queryDrawer.testEnv,
      }
    queryDrawer.loading = true
    queryDrawer.result = null
    try {
      const response = await (relational
        ? queryLogicalDataSource({ ...target, sql: statement })
        : postDataSourceExecution({ ...target, action: 'execute', operation_config }))
      if (current !== request || !scope.current(version)) return
      queryDrawer.result = response.data ?? {}
      Message.success(response.msg)
    } catch (error: unknown) {
      if (!relational && current === request && scope.current(version))
        Message.error(requestError(error))
    } finally {
      if (current === request) queryDrawer.loading = false
    }
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-sql-query-drawer {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    height: 100%;
  }

  .mango-sql-query-editor {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .mango-datasource-query-field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mango-sql-query-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .mango-sql-query-meta {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .mango-sql-query-label {
    flex: none;
    color: var(--m-text);
    font-size: 13px;
  }

  .mango-sql-query-result {
    min-height: 0;
    flex: 1;
  }

  .mango-datasource-query-loading {
    display: block;
    min-height: 240px;
  }

  .mango-sql-query-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 13px;
  }
</style>
