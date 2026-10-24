<template>
  <div
    class="mango-pytest-result-detail"
    :class="{ 'has-context': errorMessage || sourceSnapshot }"
  >
    <div v-if="errorMessage || sourceSnapshot" class="mango-pytest-result-detail__context">
      <a-alert v-if="errorMessage" type="error" class="mango-pytest-result-detail__alert">
        {{ errorMessage }}
      </a-alert>
      <div v-if="sourceSnapshot" class="mango-pytest-result-detail__source">
        <strong>{{ sourceSnapshot.repository_name || '默认 Pytest 仓库' }}</strong>
        <span>/</span>
        <span>{{
          sourceSnapshot.pytest_project_name || `项目 ${sourceSnapshot.pytest_project_id}`
        }}</span>
        <a-tag size="small">{{ sourceSnapshot.branch || '-' }}</a-tag>
        <a-tag size="small" color="arcoblue">{{ shortCommit }}</a-tag>
        <span class="mango-pytest-result-detail__source-path" :title="sourceSnapshot.file_path">
          {{ sourceSnapshot.file_path }}
        </span>
      </div>
    </div>

    <section class="mango-pytest-result-detail__cases">
      <div class="mango-pytest-result-detail__head">
        <strong>本次执行 Case</strong>
        <span>{{ executionCases.length }} 条</span>
      </div>
      <div class="mango-pytest-result-detail__case-list mango-native-scrollbar">
        <button
          v-for="(item, index) in executionCases"
          :key="caseKey(item, index)"
          v-memo="[
            caseKey(item, index),
            caseName(item, index),
            caseDescription(item),
            item?.status,
            selectedCaseKey,
          ]"
          type="button"
          class="mango-pytest-result-detail__case"
          :class="[
            `mango-pytest-result-detail__case--${statusTone(item?.status)}`,
            { active: caseKey(item, index) === selectedCaseKey },
          ]"
          @click="selectedCaseKey = caseKey(item, index)"
        >
          <span class="mango-pytest-result-detail__case-title">
            <strong :title="caseName(item, index)">{{ caseName(item, index) }}</strong>
            <a-tag :color="statusColor(item?.status)" size="small">
              {{ statusText(item?.status) }}
            </a-tag>
          </span>
          <small v-if="caseDescription(item)" :title="caseDescription(item)">
            {{ caseDescription(item) }}
          </small>
        </button>
        <div v-if="!executionCases.length" class="mango-empty-state">
          {{ emptyDescription }}
        </div>
      </div>
    </section>

    <PytestTestReport
      v-if="selectedCase"
      class="mango-pytest-result-detail__content mango-native-scrollbar"
      :result-data="selectedCase"
    />
    <div v-else class="mango-pytest-result-detail__content mango-empty-state">
      请选择本次执行中的 Case 查看结果
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import PytestTestReport from '@/components/reports/PytestTestReport.vue'

  const props = withDefaults(
    defineProps<{
      detail?: any
      errorMessage?: string
    }>(),
    {
      detail: null,
      errorMessage: '',
    }
  )

  const selectedCaseKey = ref('')
  const sourceSnapshot = computed(() => props.detail?.source_snapshot || null)
  const shortCommit = computed(() => String(sourceSnapshot.value?.commit_hash || '-').slice(0, 10))
  const executionCases = computed<any[]>(() => {
    const resultData = props.detail?.result_data
    if (Array.isArray(resultData)) return resultData.filter(Boolean)
    if (Array.isArray(resultData?.children)) return resultData.children.filter(Boolean)
    if (Array.isArray(resultData?.cases)) return resultData.cases.filter(Boolean)
    if (Array.isArray(resultData?.results)) return resultData.results.filter(Boolean)
    return resultData && typeof resultData === 'object' ? [resultData] : []
  })
  const selectedCase = computed(
    () =>
      executionCases.value.find((item, index) => caseKey(item, index) === selectedCaseKey.value) ||
      null
  )
  const emptyDescription = computed(() => {
    if (!props.detail) return '请选择左侧执行记录'
    if (props.detail.result_cleaned) return '结果明细已按保留策略清理，执行记录仍然保留'
    return '本次执行没有生成 Case 结果'
  })

  function caseKey(item: any, index: number) {
    const identity = item?.uuid || item?.nodeid || item?.fullName || item?.name || 'case'
    return `${identity}:${index}`
  }

  function caseName(item: any, index: number) {
    return item?.name || item?.title || item?.method_name || `Case ${index + 1}`
  }

  function caseDescription(item: any) {
    return item?.fullName || item?.description || item?.nodeid || ''
  }

  function normalizedStatus(status: unknown) {
    return String(status ?? '').toLocaleLowerCase()
  }

  function statusText(status: unknown) {
    const value = normalizedStatus(status)
    if (status === 1 || value === 'passed' || value === 'success') return '通过'
    if (status === 0 || value === 'failed' || value === 'broken') return '失败'
    if (value === 'skipped') return '跳过'
    if (status === 3 || value === 'running') return '进行中'
    return '未知'
  }

  function statusColor(status: unknown) {
    const value = normalizedStatus(status)
    if (status === 1 || value === 'passed' || value === 'success') return 'green'
    if (status === 0 || value === 'failed' || value === 'broken') return 'red'
    if (value === 'skipped') return 'orange'
    if (status === 3 || value === 'running') return 'arcoblue'
    return 'gray'
  }

  function statusTone(status: unknown) {
    const value = normalizedStatus(status)
    if (status === 1 || value === 'passed' || value === 'success') return 'success'
    if (status === 0 || value === 'failed' || value === 'broken') return 'danger'
    if (value === 'skipped') return 'warning'
    if (status === 3 || value === 'running') return 'running'
    return 'neutral'
  }

  watch(
    [() => props.detail?.id, executionCases],
    () => {
      const failedIndex = executionCases.value.findIndex((item) => {
        const status = normalizedStatus(item?.status)
        return item?.status === 0 || status === 'failed' || status === 'broken'
      })
      const preferredIndex = failedIndex >= 0 ? failedIndex : 0
      const preferred = executionCases.value[preferredIndex]
      selectedCaseKey.value = preferred ? caseKey(preferred, preferredIndex) : ''
    },
    { immediate: true }
  )
</script>

<style lang="less" scoped>
  .mango-pytest-result-detail {
    display: grid;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    grid-template-columns: 300px minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
    gap: 12px;
  }

  .mango-pytest-result-detail.has-context {
    grid-template-rows: auto minmax(0, 1fr);
  }

  .mango-pytest-result-detail__context {
    display: flex;
    grid-column: 1 / -1;
    min-width: 0;
    flex-direction: column;
    gap: 8px;
  }

  .mango-pytest-result-detail__source {
    display: flex;
    min-width: 0;
    min-height: 36px;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    color: var(--m-text-2);
    background: var(--m-surface-soft);
    font-size: 12px;
  }

  .mango-pytest-result-detail__source strong {
    color: var(--m-text);
  }

  .mango-pytest-result-detail__source-path {
    min-width: 0;
    margin-left: auto;
    overflow: hidden;
    color: var(--m-muted);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-result-detail__cases {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    overflow: hidden;
  }

  .mango-pytest-result-detail__head {
    display: flex;
    min-height: 40px;
    flex: 0 0 auto;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    padding: 9px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-pytest-result-detail__head strong {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
  }

  .mango-pytest-result-detail__head span,
  .mango-pytest-result-detail__case small {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-pytest-result-detail__case-list {
    flex: 1;
    overflow: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .mango-pytest-result-detail__case {
    --mango-pytest-case-tone: var(--m-primary);

    display: flex;
    width: 100%;
    flex-direction: column;
    gap: 5px;
    padding: 10px 12px;
    border: 0;
    border-bottom: 1px solid var(--m-border);
    background: color-mix(in srgb, var(--mango-pytest-case-tone) 3%, var(--m-surface));
    color: var(--m-text);
    cursor: pointer;
    text-align: left;
    transition: background var(--m-motion-duration-fast), box-shadow var(--m-motion-duration-fast);
  }

  .mango-pytest-result-detail__case:hover {
    background: color-mix(in srgb, var(--mango-pytest-case-tone) 7%, var(--m-surface));
  }

  .mango-pytest-result-detail__case:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -2px;
  }

  .mango-pytest-result-detail__case.active {
    background: color-mix(in srgb, var(--mango-pytest-case-tone) 11%, var(--m-surface));
    box-shadow: inset 3px 0 0 var(--mango-pytest-case-tone);
  }

  .mango-pytest-result-detail__case--success {
    --mango-pytest-case-tone: var(--m-success);
  }

  .mango-pytest-result-detail__case--danger {
    --mango-pytest-case-tone: var(--m-danger);
  }

  .mango-pytest-result-detail__case--warning {
    --mango-pytest-case-tone: var(--m-warning);
  }

  .mango-pytest-result-detail__case--running {
    --mango-pytest-case-tone: var(--m-primary);
  }

  .mango-pytest-result-detail__case--neutral {
    --mango-pytest-case-tone: var(--m-border-strong);
  }

  .mango-pytest-result-detail__case-title {
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-pytest-result-detail__case-title strong,
  .mango-pytest-result-detail__case small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-result-detail__case-title strong {
    min-width: 0;
    font-size: 13px;
    font-weight: 600;
  }

  .mango-pytest-result-detail__case-list > .mango-empty-state,
  .mango-pytest-result-detail__content.mango-empty-state {
    margin-top: 96px;
  }

  .mango-pytest-result-detail__content {
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  @media (max-width: 1100px) {
    .mango-pytest-result-detail {
      grid-template-columns: 1fr;
      grid-template-rows: minmax(180px, 30%) minmax(0, 1fr);
    }

    .mango-pytest-result-detail.has-context {
      grid-template-rows: auto minmax(180px, 30%) minmax(0, 1fr);
    }
  }
</style>
