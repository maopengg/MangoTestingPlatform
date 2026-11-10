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
            :disabled="loading || saving || aiInferring"
            size="small"
            allow-search
            placeholder="请选择项目绑定"
            @change="requestScopeChange"
          />
          <a-button
            type="outline"
            size="small"
            :loading="aiInferring"
            :disabled="loading || saving || aiInferring || loadFailed || !rows.length"
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
              <a-input v-model="record.name" :disabled="saving || aiInferring || loading" size="small" placeholder="请输入用例名称" />
            </template>
          </a-table-column>
          <a-table-column title="所属模块" :width="260">
            <template #cell="{ record }">
              <ProductModuleSelect
                v-model="record.module"
                :disabled="saving || aiInferring || loading"
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
                :disabled="saving || aiInferring || loading"
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
                :disabled="saving || aiInferring || loading"
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
                :disabled="saving || aiInferring || loading"
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
                :disabled="saving || aiInferring || loading"
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
                :disabled="saving || aiInferring || loading"
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
                :disabled="saving || aiInferring || loading"
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
                :disabled="saving || aiInferring || loading"
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

        </template>
      </a-table>
    </div>

    <template #footer-buttons>
      <a-button @click="close">取消</a-button>
      <a-button  type="primary" :loading="saving" :disabled="loading || saving || aiInferring || loadFailed || !rows.length" @click="save">
        保存修改
      </a-button>
    </template>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { getPytestCase, postPytestCaseAiInfer, putPytestCaseBatchUpdate } from '@/api/pytest/case'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { fieldNames } from '@/setting'
  import { batchChanges, batchId, batchScopeIds, batchValues, readBatchPredictions, readBatchRows, readBatchSaveCount, validateBatchRows } from '../batch-editor'
  import type { BatchRow, BatchScope, BatchUserOption, BatchValues } from '../batch-editor'

  const props = withDefaults(defineProps<{
    visible?: boolean; scopes?: BatchScope[]; initialScopeKey?: string
    userOptions?: BatchUserOption[]; currentUserId?: string | number | null
  }>(), { visible: false, scopes: () => [], initialScopeKey: '', userOptions: () => [], currentUserId: null })
  const emit = defineEmits<{
    (event: 'update:visible', visible: boolean): void
    (event: 'saved', updatedCount: number): void
  }>()
  const enumStore = useEnum(), user = useUserStore(), route = useRoute()
  const localVisible = ref(false), loading = ref(false), saving = ref(false), aiInferring = ref(false), loadFailed = ref(false)
  const rows = ref<BatchRow[]>([]), originals = ref(new Map<number, BatchValues>()), selectedScopeKey = ref('')
  let windowVersion = 0, readVersion = 0, active = true, disposed = false, needsRead = false
  let pendingRead: { current: () => boolean; promise: Promise<boolean> } | null = null
  let scopeConfirmation: ReturnType<typeof Modal.confirm> | null = null
  let confirmationVersion = 0
  const available = () => !disposed && active && localVisible.value && (typeof document === 'undefined' || !document.hidden)
  const activeScope = computed(() => props.scopes.find(scope => scope.key === selectedScopeKey.value) || null)
  const scopeOptions = computed(() => props.scopes.map(scope => ({
    label: scope.label + '（' + scope.caseIds.length + ' 条）', value: scope.key,
    disabled: scope.disabled || !scope.caseIds.length || scope.caseIds.length > 500,
  })))
  const changedFields = (row: BatchRow) => batchChanges(row, originals.value.get(row.id))
  const changedCount = computed(() => rows.value.filter(row => Object.keys(changedFields(row)).length).length)
  function assetStatusOptions(row: BatchRow) {
    return (enumStore.pytest_asset_status || []).filter(option => row.publication_status === 'prepublished'
      ? Number(option.key) === Number(row.asset_status)
      : (Number(option.key) === 1) === (row.publication_status === 'published'))
  }
  function closeScopeConfirmation(): void { confirmationVersion++; scopeConfirmation?.close(); scopeConfirmation = null }
  function invalidate(): void {
    windowVersion++; readVersion++; pendingRead = null; loading.value = false; loadFailed.value = false
    rows.value = []; originals.value = new Map(); needsRead = true
    closeScopeConfirmation()
  }
  function close(): void {
    if (localVisible.value) localVisible.value = false
    else invalidate()
  }
  function open(): void {
    invalidate()
    selectedScopeKey.value = props.scopes.find(scope => scope.key === props.initialScopeKey && !scope.disabled)?.key ||
      props.scopes.find(scope => !scope.disabled)?.key || ''
    localVisible.value = true
    if (!available()) { close(); return }
    void loadRows()
  }
  function loadRows(): Promise<boolean> {
    if (!available()) return Promise.resolve(false)
    if (saving.value || aiInferring.value) { needsRead = true; return Promise.resolve(false) }
    if (pendingRead?.current()) return pendingRead.promise
    let ids: number[]
    try { ids = batchScopeIds(activeScope.value) }
    catch (loadFailure0) { (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true); return Promise.resolve(false) }
    const window = windowVersion, request = ++readVersion
    const current = () => available() && window === windowVersion && request === readVersion
    loading.value = true; loadFailed.value = false
    const job = { current, promise: Promise.resolve(false) }
    pendingRead = job
    job.promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const response = await getPytestCase({ id__in: ids.join(','), page: 1, pageSize: ids.length })
        if (!current()) return false
        const next = readBatchRows(response, ids)
        rows.value = next
        originals.value = new Map(next.map(row => [row.id, batchValues(row)]))
        needsRead = false
        return true
      } catch (loadFailure1) {
        if (current()) (reportLoadError(loadFailure1, "加载失败，请重试", false), loadFailed.value = true)
        return false
      } finally {
        if (pendingRead === job) { pendingRead = null; loading.value = false }
      }
    })
    return job.promise
  }
  async function save(): Promise<boolean> {
    if (!available() || saving.value || aiInferring.value || loading.value || loadFailed.value) return false
    const changed = rows.value.filter(row => Object.keys(changedFields(row)).length)
    if (!changed.length) { Message.warning('当前没有需要保存的修改'); return false }
    const error = validateBatchRows(changed)
    if (error) { Message.error(error); return false }
    const updates = changed.map(row => ({ id: row.id, changes: changedFields(row) }))
    const window = windowVersion
    const current = () => available() && window === windowVersion
    saving.value = true
    try {
      const count = readBatchSaveCount(await putPytestCaseBatchUpdate({ updates }), updates.length)
      if (!current()) return false
      Message.success('已保存 ' + count + ' 条 Case')
      close()
      emit('saved', count)
      return true
    } catch {
      if (current()) Message.error('批量保存失败，请重试')
      return false
    } finally {
      saving.value = false
      if (available() && needsRead) void loadRows()
    }
  }
  async function inferWithAi(): Promise<boolean> {
    if (!available() || saving.value || aiInferring.value || loading.value || loadFailed.value) return false
    let ids: number[], currentUserId: number
    try { ids = batchScopeIds(activeScope.value); currentUserId = batchId(props.currentUserId) }
    catch { Message.error('请检查编辑范围和当前登录用户'); return false }
    const window = windowVersion, baseline = new Map(rows.value.map(row => [row.id, { ...batchValues(row), name: row.name }]))
    const current = () => available() && window === windowVersion
    aiInferring.value = true
    try {
      const response = await postPytestCaseAiInfer({ case_ids: [...ids] })
      if (!current()) return false
      const predictions = readBatchPredictions(response, ids)
      for (const row of rows.value) {
        const before = baseline.get(row.id)
        if (!before) continue
        const prediction = predictions.get(row.id)
        if (prediction) for (const field of Object.keys(prediction) as Array<keyof BatchValues>) {
          if (JSON.stringify(row[field]) === JSON.stringify(before[field])) Object.assign(row, { [field]: prediction[field] })
        }
        if (row.case_people === before.case_people) row.case_people = currentUserId
      }
      Message.success('已生成 ' + predictions.size + ' 条推断建议，请确认后保存')
      return true
    } catch {
      if (current()) Message.error('AI 推断失败，请重试')
      return false
    } finally {
      aiInferring.value = false
      if (available() && needsRead) void loadRows()
    }
  }
  function applyScopeChange(key: string): void {
    invalidate(); selectedScopeKey.value = key; void loadRows()
  }
  function requestScopeChange(value: string | number | boolean): void {
    if (!available() || loading.value || saving.value || aiInferring.value) return
    const key = String(value), target = props.scopes.find(scope => scope.key === key)
    if (!target || key === selectedScopeKey.value) return
    try { batchScopeIds(target) } catch { return }
    if (!changedCount.value) { applyScopeChange(key); return }
    closeScopeConfirmation()
    const window = windowVersion, confirmation = confirmationVersion
    scopeConfirmation = Modal.confirm({
      title: '切换编辑项目',
      content: '当前有 ' + changedCount.value + ' 条未保存修改，切换后这些修改将丢失。确定继续吗？',
      okText: '继续切换', cancelText: '取消',
      onBeforeOk: () => {
        if (!available() || window !== windowVersion || confirmation !== confirmationVersion || saving.value || aiInferring.value) return false
        applyScopeChange(key); return true
      },
    })
  }
  watch(localVisible, visible => {
    if (!visible) invalidate()
    emit('update:visible', visible)
  }, { flush: 'sync' })
  watch(() => [props.visible, props.initialScopeKey, JSON.stringify(props.scopes)], () => {
    if (props.visible) open()
    else close()
  }, { immediate: true })
  watch(() => [user.userId, user.roleId, user.token, user.selected_environment], close, { flush: 'sync' })
  watch(() => route.fullPath, close, { flush: 'sync' })
  function onVisibilityChange(): void { if (document.hidden) close() }
  onMounted(() => { if (typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisibilityChange) })
  onActivated(() => { active = true })
  onDeactivated(() => { active = false; close() })
  onBeforeUnmount(() => { disposed = true; close(); if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisibilityChange) })
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
