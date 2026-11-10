<template>
  <div
    class="mango-pytest-result-detail"
    :class="{ 'has-context': errorMessage || sourceSnapshot || detailState.malformed }"
  >
    <div v-if="errorMessage || sourceSnapshot || detailState.malformed" class="mango-pytest-result-detail__context">
      <a-alert v-if="errorMessage" type="error" class="mango-pytest-result-detail__alert">
        {{ errorMessage }}
      </a-alert>
      <a-alert v-if="detailState.malformed" type="warning">部分结果格式异常，无法展示对应 Case，请重新加载执行记录。</a-alert>
      <div v-if="sourceSnapshot" class="mango-pytest-result-detail__source">
        <strong>{{ sourceSnapshot.repositoryName }}</strong>
        <span>/</span>
        <span>{{
          sourceSnapshot.projectName
        }}</span>
        <a-tag size="small">{{ sourceSnapshot.branch }}</a-tag>
        <a-tag size="small" color="arcoblue">{{ sourceSnapshot.commit }}</a-tag>
        <span class="mango-pytest-result-detail__source-path" :title="sourceSnapshot.filePath">
          {{ sourceSnapshot.filePath }}
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
          v-for="item in executionCases"
          :key="item.key"
          type="button"
          class="mango-pytest-result-detail__case"
          :class="[
            `mango-pytest-result-detail__case--${resultStatus(item.status).tone}`,
            { active: item.key === selectedCaseKey },
          ]"
          @click="selectedCaseKey = item.key"
        >
          <span class="mango-pytest-result-detail__case-title">
            <strong :title="item.name">{{ item.name }}</strong>
            <a-tag :color="resultStatus(item.status).color" size="small">
              {{ resultStatus(item.status).text }}
            </a-tag>
          </span>
          <small v-if="item.description" :title="item.description">
            {{ item.description }}
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
      :result-data="selectedCase.payload"
    />
    <div v-else class="mango-pytest-result-detail__content mango-empty-state">
      请选择本次执行中的 Case 查看结果
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import PytestTestReport from '@/components/reports/PytestTestReport.vue'
  import { executionDetail, resultStatus } from '../execution-result'

  const props = withDefaults(
    defineProps<{
      detail?: unknown
      errorMessage?: string
    }>(),
    {
      detail: null,
      errorMessage: '',
    }
  )

  const selectedCaseKey = ref('')
  const detailState = computed(() => executionDetail(props.detail))
  const sourceSnapshot = computed(() => detailState.value.source)
  const executionCases = computed(() => detailState.value.cases)
  const selectedCase = computed(
    () =>
      executionCases.value.find((item) => item.key === selectedCaseKey.value) ||
      null
  )
  const emptyDescription = computed(() => {
    if (!detailState.value.present) return '请选择左侧执行记录'
    if (detailState.value.cleaned) return '结果明细已按保留策略清理，执行记录仍然保留'
    if (detailState.value.malformed) return '结果格式异常'
    return '本次执行没有生成 Case 结果'
  })

  watch(
    detailState,
    (next, previous) => {
      if (next.id === previous?.id && next.cases.some(item => item.key === selectedCaseKey.value)) return
      const failedIndex = executionCases.value.findIndex(item => resultStatus(item.status).tone === 'danger')
      const preferredIndex = failedIndex >= 0 ? failedIndex : 0
      const preferred = executionCases.value[preferredIndex]
      selectedCaseKey.value = preferred?.key || ''
    },
    { immediate: true, flush: 'sync' }
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
