<template>
  <BaseSidePanel
    v-model:visible="localVisible"
    title="批量编辑 Case"
    width="min(1280px, 78vw)"
    :mask-closable="false"
    @cancel="close"
  >
    <div class="mango-pytest-batch-editor">
      <div class="mango-pytest-batch-editor__summary">
        <div class="mango-pytest-batch-editor__scope">
          <span>编辑范围</span>
          <a-select
            :model-value="selectedScopeKey"
            :options="scopeOptions"
            size="small"
            allow-search
            placeholder="请选择项目绑定"
            @change="requestScopeChange"
          />
          <a-button
            type="outline"
            size="small"
            :loading="aiInferring"
            :disabled="loading || !rows.length"
            @click="inferWithAi"
          >
            <template #icon><icon-robot /></template>
            AI 推断
          </a-button>
        </div>
        <a-space size="mini">
          <a-tag>共 {{ rows.length }} 条</a-tag>
          <a-tag :color="changedCount ? 'arcoblue' : 'gray'">已修改 {{ changedCount }} 条</a-tag>
        </a-space>
      </div>

      <a-table
        class="mango-native-scroll-table mango-pytest-batch-editor__table"
        row-key="id"
        :data="rows"
        :loading="loading"
        :pagination="false"
        :bordered="{ cell: true }"
        :scroll="{ x: 1960, y: 'calc(100vh - 232px)' }"
      >
        <template #columns>
          <a-table-column title="ID" data-index="id" :width="70" fixed="left" />
          <a-table-column title="项目/产品" :width="170" fixed="left">
            <template #cell="{ record }">
              <span class="mango-pytest-batch-editor__readonly" :title="record.projectProductLabel">
                {{ record.projectProductLabel }}
              </span>
            </template>
          </a-table-column>
          <a-table-column title="用例名称" :width="220">
            <template #cell="{ record }">
              <a-input v-model="record.name" size="small" placeholder="请输入用例名称" />
            </template>
          </a-table-column>
          <a-table-column title="所属模块" :width="260">
            <template #cell="{ record }">
              <ProductModuleSelect
                v-model="record.module"
                :project-product-id="record.projectProductId"
                :allow-clear="false"
                placeholder="请选择所属模块"
              />
            </template>
          </a-table-column>
          <a-table-column title="资产状态" :width="130">
            <template #cell="{ record }">
              <a-select
                v-model="record.asset_status"
                size="small"
                :options="assetStatusOptions(record)"
                :field-names="fieldNames"
              />
            </template>
          </a-table-column>
          <a-table-column title="优先级" :width="110">
            <template #cell="{ record }">
              <a-select
                v-model="record.level"
                size="small"
                :options="enumStore.case_level"
                :field-names="fieldNames"
              />
            </template>
          </a-table-column>
          <a-table-column title="测试层级" :width="140">
            <template #cell="{ record }">
              <a-select
                v-model="record.scenario_layer"
                size="small"
                :options="enumStore.api_case_scenario_layer"
                :field-names="fieldNames"
              />
            </template>
          </a-table-column>
          <a-table-column title="验证类型" :width="140">
            <template #cell="{ record }">
              <a-select
                v-model="record.scenario_type"
                size="small"
                :options="enumStore.api_case_scenario_type"
                :field-names="fieldNames"
              />
            </template>
          </a-table-column>
          <a-table-column title="执行场景" :width="230">
            <template #cell="{ record }">
              <a-select
                v-model="record.scenario_tags"
                size="small"
                multiple
                allow-search
                :max-tag-count="1"
                :options="enumStore.api_case_scenario_tag"
                :field-names="fieldNames"
                placeholder="请选择执行场景"
              />
            </template>
          </a-table-column>
          <a-table-column title="场景描述" :width="240">
            <template #cell="{ record }">
              <a-input
                v-model="record.scenario_description"
                size="small"
                allow-clear
                placeholder="请输入场景描述"
              />
            </template>
          </a-table-column>
          <a-table-column title="用例负责人" :width="160">
            <template #cell="{ record }">
              <a-select
                v-model="record.case_people"
                size="small"
                allow-search
                :options="userOptions"
                :field-names="fieldNames"
                placeholder="请选择负责人"
              />
            </template>
          </a-table-column>
        </template>
        <template #empty>
          <div class="mango-empty-state">当前范围没有可编辑的 Case</div>
        </template>
      </a-table>
    </div>

    <template #footer-buttons>
      <a-button @click="close">取消</a-button>
      <a-button  type="primary" :loading="saving" :disabled="loading || !rows.length" @click="save">
        保存修改
      </a-button>
    </template>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    getPytestCase,
    postPytestCaseAiInfer,
    putPytestCaseBatchUpdate,
  } from '@/api/pytest/case'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'

  type BatchRow = {
    id: number
    projectProductId: number | null
    projectProductLabel: string
    name: string
    module: any
    asset_status: number | string | null
    publication_status: string
    level: number | string | null
    scenario_layer: number | string | null
    scenario_type: number | string | null
    scenario_tags: Array<number | string>
    scenario_description: string
    case_people: number | string | null
  }

  type BatchScope = {
    key: string
    label: string
    caseIds: number[]
    disabled?: boolean
  }

  const props = withDefaults(
    defineProps<{
      visible?: boolean
      scopes?: BatchScope[]
      initialScopeKey?: string
      userOptions?: any[]
      currentUserId?: number | string | null
    }>(),
    {
      visible: false,
      scopes: () => [],
      initialScopeKey: '',
      userOptions: () => [],
      currentUserId: null,
    }
  )
  const emit = defineEmits<{
    (event: 'update:visible', value: boolean): void
    (event: 'saved', updatedCount: number): void
  }>()

  const enumStore = useEnum()
  const localVisible = ref(false)
  const loading = ref(false)
  const saving = ref(false)
  const aiInferring = ref(false)
  const rows = ref<BatchRow[]>([])
  const originals = ref(new Map<number, Record<string, unknown>>())
  const selectedScopeKey = ref('')
  let requestVersion = 0

  const activeScope = computed(
    () => props.scopes.find((scope) => scope.key === selectedScopeKey.value) || null
  )
  const scopeOptions = computed(() =>
    props.scopes.map((scope) => ({
      label: `${scope.label}（${scope.caseIds.length} 条）`,
      value: scope.key,
      disabled: scope.disabled,
    }))
  )

  const editableFields = [
    'name',
    'module',
    'asset_status',
    'level',
    'scenario_layer',
    'scenario_type',
    'scenario_tags',
    'scenario_description',
    'case_people',
  ] as const

  function editableValues(row: BatchRow) {
    return {
      name: row.name.trim(),
      module: getOptionId(row.module),
      asset_status: row.asset_status,
      level: row.level,
      scenario_layer: row.scenario_layer,
      scenario_type: row.scenario_type,
      scenario_tags: [...(row.scenario_tags || [])],
      scenario_description: row.scenario_description || '',
      case_people: getOptionId(row.case_people),
    }
  }

  function changedFields(row: BatchRow) {
    const current = editableValues(row)
    const original = originals.value.get(row.id) || {}
    return Object.fromEntries(
      editableFields
        .filter((key) => JSON.stringify(current[key]) !== JSON.stringify(original[key]))
        .map((key) => [key, current[key]])
    )
  }

  const changedCount = computed(
    () => rows.value.filter((row) => Object.keys(changedFields(row)).length > 0).length
  )

  function normalizeRecord(record: any): BatchRow {
    return {
      id: Number(record.id),
      projectProductId: Number(record.project_product?.project_product?.id) || null,
      projectProductLabel: formatProjectProductPath(record.project_product),
      name: String(record.name || ''),
      module: record.module?.id ?? null,
      asset_status: record.asset_status ?? 0,
      publication_status: record.publication_status,
      level: record.level ?? null,
      scenario_layer: record.scenario_layer ?? 0,
      scenario_type: record.scenario_type ?? 0,
      scenario_tags: Array.isArray(record.scenario_tags) ? [...record.scenario_tags] : [],
      scenario_description: String(record.scenario_description || ''),
      case_people: record.case_people?.id ?? null,
    }
  }

  function assetStatusOptions(row: BatchRow) {
    return (enumStore.pytest_asset_status || []).filter((option: any) =>
      row.publication_status === 'prepublished'
        ? Number(option.key) === Number(row.asset_status)
        : (Number(option.key) === 1) === (row.publication_status === 'published')
    )
  }

  async function loadRows() {
    const version = ++requestVersion
    rows.value = []
    originals.value = new Map()
    const caseIds = activeScope.value?.caseIds || []
    if (!caseIds.length) return
    loading.value = true
    try {
      const res = await getPytestCase({
        id__in: caseIds.join(','),
        page: 1,
        pageSize: caseIds.length,
      })
      if (version !== requestVersion) return
      const order = new Map(caseIds.map((id, index) => [Number(id), index]))
      rows.value = (Array.isArray(res.data) ? res.data : [])
        .map(normalizeRecord)
        .sort((left, right) => (order.get(left.id) || 0) - (order.get(right.id) || 0))
      originals.value = new Map(rows.value.map((row) => [row.id, editableValues(row)]))
    } finally {
      if (version === requestVersion) loading.value = false
    }
  }

  function validateRows(targetRows: BatchRow[]) {
    for (const row of targetRows) {
      if (!row.name.trim()) return `Case ${row.id} 的用例名称不能为空`
      if (!getOptionId(row.module)) return `Case ${row.id} 请选择所属模块`
      if (row.asset_status === null || row.asset_status === '')
        return `Case ${row.id} 请选择资产状态`
      if (row.level === null || row.level === '') return `Case ${row.id} 请选择优先级`
      if (row.scenario_layer === null || row.scenario_layer === '')
        return `Case ${row.id} 请选择测试层级`
      if (row.scenario_type === null || row.scenario_type === '')
        return `Case ${row.id} 请选择验证类型`
      if (!row.scenario_tags?.length) return `Case ${row.id} 请选择执行场景`
      if (!getOptionId(row.case_people)) return `Case ${row.id} 请选择用例负责人`
    }
    return ''
  }

  async function save() {
    const changedRows = rows.value.filter((row) => Object.keys(changedFields(row)).length > 0)
    if (!changedRows.length) {
      Message.warning('当前没有需要保存的修改')
      return
    }
    const errorMessage = validateRows(changedRows)
    if (errorMessage) {
      Message.error(errorMessage)
      return
    }
    saving.value = true
    try {
      const res = await putPytestCaseBatchUpdate({
        updates: changedRows.map((row) => ({ id: row.id, changes: changedFields(row) })),
      })
      const updatedCount = Number(res.data?.updated_count || changedRows.length)
      Message.success(res.msg || `已保存 ${updatedCount} 条 Case`)
      emit('saved', updatedCount)
      close()
    } finally {
      saving.value = false
    }
  }

  async function inferWithAi() {
    const caseIds = activeScope.value?.caseIds || []
    const currentUserId = getOptionId(props.currentUserId)
    if (!caseIds.length) {
      Message.warning('当前编辑范围没有可推断的 Case')
      return
    }
    if (!currentUserId) {
      Message.error('未获取到当前登录用户，无法设置用例负责人')
      return
    }
    aiInferring.value = true
    try {
      const res = await postPytestCaseAiInfer({ case_ids: caseIds.map(Number) })
      const predictions = Array.isArray(res.data?.predictions) ? res.data.predictions : []
      const predictionMap = new Map(predictions.map((item: any) => [Number(item.id), item]))
      const inferredFields = [
        'name',
        'module',
        'asset_status',
        'level',
        'scenario_layer',
        'scenario_type',
        'scenario_tags',
        'scenario_description',
      ] as const
      rows.value.forEach((row) => {
        const prediction = predictionMap.get(row.id)
        if (prediction) {
          inferredFields.forEach((field) => {
            if (prediction[field] !== undefined) {
              const inferredValue =
                field === 'scenario_tags' && Array.isArray(prediction[field])
                  ? [...prediction[field]]
                  : prediction[field]
              Object.assign(row, { [field]: inferredValue })
            }
          })
        }
        row.case_people = currentUserId
      })
      Message.success(
        `已推断 ${predictions.length} 条 Case，资产状态已设为已发布，负责人已设为当前登录用户；请确认后保存`
      )
    } finally {
      aiInferring.value = false
    }
  }

  function close() {
    localVisible.value = false
  }

  function applyScopeChange(scopeKey: string) {
    selectedScopeKey.value = scopeKey
    void loadRows()
  }

  function requestScopeChange(value: string | number | boolean) {
    const scopeKey = String(value)
    if (!scopeKey || scopeKey === selectedScopeKey.value) return
    if (!changedCount.value) {
      applyScopeChange(scopeKey)
      return
    }
    Modal.confirm({
      title: '切换编辑项目',
      content: `当前有 ${changedCount.value} 条未保存修改，切换后这些修改将丢失。确定继续吗？`,
      okText: '继续切换',
      cancelText: '取消',
      onBeforeOk: () => {
        applyScopeChange(scopeKey)
        return true
      },
    })
  }

  watch(
    () => props.visible,
    (visible) => {
      localVisible.value = visible
      if (visible) {
        selectedScopeKey.value =
          props.initialScopeKey || props.scopes.find((scope) => !scope.disabled)?.key || ''
        void loadRows()
      }
    },
    { immediate: true }
  )
  watch(localVisible, (visible) => emit('update:visible', visible))
</script>

<style lang="less" scoped>
  .mango-pytest-batch-editor {
    box-sizing: border-box;
    display: flex;
    height: 100%;
    min-height: 0;
    padding: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
    overflow: hidden;
    background: var(--m-bg);
  }

  .mango-pytest-batch-editor__summary {
    display: flex;
    min-height: 36px;
    flex: 0 0 auto;
    padding: 6px 10px;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-pytest-batch-editor__scope {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;

    span {
      flex: 0 0 auto;
      color: var(--m-muted);
      font-size: 12px;
    }

    :deep(.arco-select-view) {
      width: min(720px, 52vw);
    }

    .arco-btn {
      flex: 0 0 auto;
    }
  }

  .mango-pytest-batch-editor__table {
    min-height: 0;
    flex: 1 1 auto;
    border-radius: var(--m-radius-md);
    background: var(--m-surface);

    :deep(.arco-table-cell) {
      padding: 7px 8px;
    }

    :deep(.arco-cascader),
    :deep(.arco-select),
    :deep(.arco-input-wrapper) {
      width: 100%;
    }

    :deep(.arco-cascader-view),
    :deep(.arco-select-view) {
      min-height: 28px;
    }
  }

  .mango-pytest-batch-editor__readonly {
    display: block;
    overflow: hidden;
    color: var(--m-text-2);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
