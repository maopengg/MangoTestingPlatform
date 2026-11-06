<template>
  <div class="mango-data-source-operation-list">
    <div v-if="dataList.length" class="mango-data-source-operation-list__body">
      <section
        v-for="(item, index) in dataList"
        :key="item.id || index"
        class="mango-data-source-operation-item"
      >
        <div
          :class="[
            'mango-data-source-operation-item__first-row',
            {
              'mango-data-source-operation-item__first-row--without-environment':
                !showEnvironment && showKey,
              'mango-data-source-operation-item__first-row--without-key':
                showEnvironment && !showKey,
              'mango-data-source-operation-item__first-row--datasource-only':
                !showEnvironment && !showKey,
            },
          ]"
        >
          <label class="mango-data-source-operation-field">
            <span class="mango-data-source-operation-field__label">逻辑数据源</span>
            <a-select
              v-model="item.datasource_alias"
              :error="isValidationVisible(index) && isDatasourceEmpty(item)"
              :options="datasourceOptions"
              :loading="datasourceLoading"
              allow-clear
              allow-search
              :disabled="disabled"
              placeholder="请选择逻辑数据源"
              @search="emit('search-datasource', $event)"
              @dropdown-reach-bottom="emit('load-more-datasources')"
              @popup-visible-change="open => open && emit('open-datasources')"
              @change="onFieldChange(item, index)" data-testid="qa-components-forms-datasourceoperationlist-select-请选择逻辑数据源"
            />
          </label>

          <label v-if="showEnvironment" class="mango-data-source-operation-field">
            <span class="mango-data-source-operation-field__label">执行环境</span>
            <a-select
              v-model="item.test_envs"
              :max-tag-count="2"
              :options="environmentOptions"
              allow-clear
              allow-search
              multiple
              :disabled="disabled"
              placeholder="留空表示全部环境"
              @change="onFieldChange(item, index)" data-testid="qa-components-forms-datasourceoperationlist-select-留空表示全部环境"
            />
          </label>

          <label v-if="showKey" class="mango-data-source-operation-field">
            <span class="mango-data-source-operation-field__label">{{ keyLabel }}</span>
            <a-input
              v-model="item[keyField]"
              allow-clear
              :disabled="disabled"
              :placeholder="keyPlaceholder"
              @blur="onFieldBlur(item, index)"
            />
          </label>

          <div class="mango-data-source-operation-actions">
            <a-button
              v-if="showTest"
              size="small"
              type="text"
              :loading="isTesting(index)"
              @click="onTestOperation(item, index)" data-testid="qa-components-forms-datasourceoperationlist-button-测试"
            >
              测试
            </a-button>
            <a-button
              v-if="showDelete"
              size="small"
              status="danger"
              type="text"
              :disabled="disabled"
              @click="onDeleteConfig(index)" data-testid="qa-components-forms-datasourceoperationlist-button-删除"
            >
              删除
            </a-button>
          </div>
        </div>

        <a-textarea
          :model-value="operationText(item)"
          :aria-label="`第 ${index + 1} 条数据库操作内容`"
          :auto-size="{ minRows: 2, maxRows: 10 }"
          :disabled="disabled"
          :error="isValidationVisible(index) && isStatementEmpty(item)"
          class="mango-data-source-operation-content"
          placeholder="请输入当前数据库的查询或操作内容"
          @update:model-value="onOperationInput(item, $event, index)"
          @blur="onOperationBlur(item, index)" data-testid="qa-components-forms-datasourceoperationlist-textarea-请输入当前数据库的查询或操作内容"
        />
      </section>
    </div>

    <div v-else class="mango-data-source-operation-empty">
      <a-empty :description="emptyText" />
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { Message, Modal, Notification } from '@arco-design/web-vue'
  import { postDataSourceExecution } from '@/api/data-source-execution'

  const ELASTICSEARCH_TYPE = 20
  const RESULT_PREVIEW_LENGTH = 1200

  interface SelectOption {
    label: string
    value: string | number
    dbType?: number
  }

  interface DataSourceOperationItem {
    id?: string | number
    datasource_alias?: string | number | null
    test_envs?: Array<string | number> | null
    key?: string
    key_list?: string | string[]
    sql?: string
    value?: string | Record<string, unknown>
    [key: string]: unknown
  }

  interface Props {
    dataList?: DataSourceOperationItem[]
    datasourceOptions?: SelectOption[]
    datasourceLoading?: boolean
    environmentOptions?: SelectOption[]
    onDeleteItem?: (index: number) => void
    onSave?: () => void
    onDraftChange?: (item: DataSourceOperationItem, index: number) => void
    emptyText?: string
    projectProductId?: string | number | null
    testEnv?: string | number | null
    operationField?: string
    keyField?: string
    keyLabel?: string
    keyPlaceholder?: string
    showEnvironment?: boolean
    showKey?: boolean
    showDelete?: boolean
    showTest?: boolean
    disabled?: boolean
  }

  const props = withDefaults(defineProps<Props>(), {
    dataList: () => [],
    datasourceOptions: () => [],
    datasourceLoading: false,
    emptyText: '暂无数据库操作配置，点击上方“增加”按钮添加',
    environmentOptions: () => [],
    operationField: 'value',
    keyField: 'key',
    keyLabel: '变量 Key',
    keyPlaceholder: '例如：user_id',
    showEnvironment: true,
    showKey: true,
    showDelete: true,
    showTest: true,
    disabled: false,
  })
  const validationRows = ref<Set<number>>(new Set())
  const testingRows = ref<Set<number>>(new Set())
  const operationDrafts = ref<Map<DataSourceOperationItem, string>>(new Map())

  const emit = defineEmits<{
    (event: 'update:item', index: number, value: any, item: any): void
    (event: 'search-datasource', value: string): void
    (event: 'load-more-datasources'): void
    (event: 'open-datasources'): void
  }>()

  function isDatasourceEmpty(item: DataSourceOperationItem) {
    return (
      item.datasource_alias === null ||
      item.datasource_alias === undefined ||
      item.datasource_alias === ''
    )
  }

  function isStatementEmpty(item: DataSourceOperationItem) {
    const value = operationText(item)
    return value.trim() === ''
  }

  function isItemValid(item: DataSourceOperationItem) {
    return !isDatasourceEmpty(item) && !isStatementEmpty(item)
  }

  function isValidationVisible(index: number) {
    return validationRows.value.has(index)
  }

  function validateAndSave(item: DataSourceOperationItem, index: number) {
    validationRows.value = new Set(validationRows.value).add(index)
    if (!isItemValid(item)) return
    props.onSave?.()
  }

  function onFieldBlur(item: DataSourceOperationItem, index: number) {
    props.onDraftChange?.(item, index)
    validateAndSave(item, index)
  }

  function selectedDatasourceType(item: DataSourceOperationItem) {
    const option = props.datasourceOptions.find(
      (candidate) => String(candidate.value) === String(item.datasource_alias)
    )
    return Number(option?.dbType)
  }

  function isElasticsearch(item: DataSourceOperationItem) {
    return selectedDatasourceType(item) === ELASTICSEARCH_TYPE
  }

  function operationText(item: DataSourceOperationItem) {
    const draft = operationDrafts.value.get(item)
    if (draft !== undefined) return draft
    const operationValue = item[props.operationField]
    if (typeof operationValue === 'string') return operationValue
    if (operationValue && typeof operationValue === 'object') {
      return JSON.stringify(operationValue, null, 2)
    }
    return ''
  }

  function onOperationInput(item: DataSourceOperationItem, value: string, index = 0) {
    if (isElasticsearch(item)) {
      const drafts = new Map(operationDrafts.value)
      drafts.set(item, value)
      operationDrafts.value = drafts
      return
    }
    item[props.operationField] = value
    props.onDraftChange?.(item, index)
  }

  function operationConfig(item: DataSourceOperationItem) {
    const text = operationText(item).trim()
    if (!isElasticsearch(item)) return text
    try {
      const parsed = JSON.parse(text)
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        throw new Error('Elasticsearch 操作内容必须是 JSON 对象')
      }
      return parsed as Record<string, unknown>
    } catch (error: any) {
      throw new Error(error?.message || 'Elasticsearch 操作内容不是合法 JSON')
    }
  }

  function commitOperationValue(item: DataSourceOperationItem) {
    const value = operationConfig(item)
    item[props.operationField] = value
    const drafts = new Map(operationDrafts.value)
    drafts.delete(item)
    operationDrafts.value = drafts
    return value
  }

  function onOperationBlur(item: DataSourceOperationItem, index: number) {
    try {
      commitOperationValue(item)
      validateAndSave(item, index)
    } catch (error: any) {
      validationRows.value = new Set(validationRows.value).add(index)
      Message.error(error?.message || '数据库操作内容格式不正确')
    }
  }

  function onFieldChange(item: DataSourceOperationItem, index: number) {
    props.onDraftChange?.(item, index)
    validateAndSave(item, index)
  }

  function onDeleteConfig(index: number) {
    validationRows.value = new Set()
    props.onDeleteItem?.(index)
  }

  function isTesting(index: number) {
    return testingRows.value.has(index)
  }

  function setTesting(index: number, testing: boolean) {
    const rows = new Set(testingRows.value)
    if (testing) rows.add(index)
    else rows.delete(index)
    testingRows.value = rows
  }

  function resultPreview(result: any) {
    const value = Array.isArray(result?.rows) && result.rows.length ? result.rows : result?.result
    if (value === undefined || value === null || value === '') {
      return `影响行数：${Number(result?.affected_rows || 0)}`
    }
    const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
    return text.length > RESULT_PREVIEW_LENGTH
      ? `${text.slice(0, RESULT_PREVIEW_LENGTH)}\n…结果较长，已截断`
      : text
  }

  function showTestResult(result: any) {
    Notification.success({
      title: '数据源测试成功',
      content: `耗时：${result?.duration_ms ?? '-'} ms\n结果：${resultPreview(result)}`,
      duration: 8000,
      closable: true,
    })
  }

  async function executeTest(item: DataSourceOperationItem, index: number, confirmWrite = false) {
    setTesting(index, true)
    try {
      const result = await postDataSourceExecution({
        action: 'execute',
        project_product_id: props.projectProductId as string | number,
        datasource_alias_id: item.datasource_alias as string | number,
        test_env: props.testEnv as string | number,
        operation_config: commitOperationValue(item),
        confirm_write: confirmWrite,
      })
      showTestResult(result.data)
      return true
    } catch (error: any) {
      const message = error?.message || error?.msg || '数据源测试失败'
      if (!confirmWrite && message.includes('包含写入行为')) {
        Modal.confirm({
          title: '确认执行写入操作',
          content: '当前内容包含数据库写入行为，将直接修改所选环境的数据。确定继续执行吗？',
          cancelText: '取消',
          okText: '继续执行',
          okButtonProps: { status: 'danger' },
          onBeforeOk: () => executeTest(item, index, true),
        })
        return false
      }
      Message.error(message)
      return false
    } finally {
      setTesting(index, false)
    }
  }

  function onTestOperation(item: DataSourceOperationItem, index: number) {
    validationRows.value = new Set(validationRows.value).add(index)
    if (!props.projectProductId) {
      Message.warning('当前用例缺少项目产品，无法测试数据库操作')
      return
    }
    if (props.testEnv === null || props.testEnv === undefined || props.testEnv === '') {
      Message.warning('请先在页面顶部选择测试环境')
      return
    }
    if (!isItemValid(item)) {
      Message.warning('请先完整填写逻辑数据源和操作内容')
      return
    }
    executeTest(item, index)
  }

  function validate() {
    validationRows.value = new Set(props.dataList.map((_, index) => index))
    return props.dataList.length > 0 && props.dataList.every(isItemValid)
  }

  defineExpose({ validate })
</script>

<style scoped>
  .mango-data-source-operation-list {
    width: 100%;
    min-width: 0;
    padding: 10px 0;
  }

  .mango-data-source-operation-list__body {
    min-width: 0;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-data-source-operation-item {
    min-width: 0;
    padding: 10px 12px 12px;
    transition: background-color 0.16s ease;
  }

  .mango-data-source-operation-item + .mango-data-source-operation-item {
    border-top: 1px solid var(--m-border);
  }

  .mango-data-source-operation-item:hover {
    background: var(--m-surface-soft);
  }

  .mango-data-source-operation-item__first-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr) minmax(0, 0.8fr) 48px;
    gap: 10px;
    margin-bottom: 8px;
  }

  .mango-data-source-operation-item__first-row--without-environment {
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr) 48px;
  }

  .mango-data-source-operation-item__first-row--without-key {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr) 48px;
  }

  .mango-data-source-operation-item__first-row--datasource-only {
    grid-template-columns: minmax(0, 1fr) 48px;
  }

  .mango-data-source-operation-actions {
    display: flex;
    align-self: end;
    flex-direction: column;
    align-items: stretch;
  }

  .mango-data-source-operation-field {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }

  .mango-data-source-operation-field__label {
    min-height: 18px;
    color: var(--m-text-2);
    font-size: 12px;
    font-weight: 500;
    line-height: 18px;
  }

  .mango-data-source-operation-content :deep(textarea) {
    line-height: 1.6;
  }

  .mango-data-source-operation-content :deep(textarea:not(:disabled)) {
    color: var(--m-text);
  }

  .mango-data-source-operation-empty {
    display: flex;
    min-height: 140px;
    align-items: center;
    justify-content: center;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface-soft);
  }
</style>
