<template>
  <a-drawer
    v-model:visible="visible"
    :width="'min(1120px, 92vw)'"
    :footer="false"
    title="Case AI 失败分析"
    class="mango-case-diagnosis-drawer"
    unmount-on-close
  >
    <div class="mango-case-diagnosis mango-native-scrollbar">
      <a-spin :loading="previewLoading" class="mango-case-diagnosis__preview">
        <div v-if="!resultId" class="mango-case-diagnosis__notice"
          >当前 Case 尚无可分析的执行记录。</div
        >
        <template v-else-if="previewError"><a-button size="small" @click="loadPreview">重新加载</a-button></template>
        <template v-else-if="preview">
          <div v-if="preview.evidence_level === 'trace'" class="mango-case-diagnosis__notice">
            完整结果不可用，本次仅根据执行链路摘要分析。
          </div>
          <div v-if="!preview.can_analyze" class="mango-case-diagnosis__notice">
            {{
              preview.status === 0
                ? '没有足够的执行证据，无法分析。'
                : '本次执行没有失败，无需 AI 分析。'
            }}
          </div>
          <template v-else>
            <section class="mango-case-diagnosis__steps" aria-label="提供的上下文">
              <h3>提供的上下文</h3>
              <div class="mango-case-diagnosis__step-list mango-native-scrollbar">
                <button
                  v-for="unit in preview.units"
                  :key="unit.unit_index"
                  type="button"
                  class="mango-case-diagnosis__step"
                  :class="{ 'is-selected': focusIndex === unit.unit_index }"
                  :aria-pressed="focusIndex === unit.unit_index"
                  :title="unit.name"
                  @click="selectUnit(unit.unit_index)"
                >
                  <span class="mango-case-diagnosis__step-index">{{ unit.unit_index + 1 }}</span>
                  <span class="mango-case-diagnosis__step-main">
                    <strong>{{ unit.name }}</strong>
                  </span>
                  <span
                    class="mango-case-diagnosis__step-status"
                    :class="
                      unit.status === 0
                        ? 'mango-case-diagnosis__step-status--fail'
                        : unit.status === 1
                        ? 'mango-case-diagnosis__step-status--pass'
                        : 'mango-case-diagnosis__step-status--other'
                    "
                  >
                    {{ unit.status === 0 ? '失败' : unit.status === 1 ? '通过' : '警告/未完成' }}
                  </span>
                </button>
              </div>
              <div class="mango-case-diagnosis__actions">
                <a-button type="primary" size="small" :loading="analysisLoading" @click="analyze"
                  >开始分析</a-button
                >
              </div>
            </section>
          </template>
        </template>
      </a-spin>
      <section v-if="analysis" class="mango-case-diagnosis__result" aria-label="Case 分析结果">
        <h3>分析结果</h3>
        <div v-if="!analysis.available" class="mango-case-diagnosis__notice" role="status">{{
          analysis.reason
        }}</div>
        <template v-else-if="analysis.analysis">
          <div class="mango-case-diagnosis__location">
            <span>失败步骤</span>
            <strong>{{ analysis.analysis.location }}</strong>
          </div>
          <div class="mango-case-diagnosis__finding">
            <strong>失败原因</strong>
            <p>{{ analysis.analysis.cause }}</p>
          </div>
          <div v-if="analysis.analysis.next_check" class="mango-case-diagnosis__next-check">
            <strong>建议检查</strong>
            <p>{{ analysis.analysis.next_check }}</p>
          </div>
          <details v-if="analysis.analysis.evidence.length" class="mango-case-diagnosis__evidence">
            <summary>判断依据（{{ analysis.analysis.evidence.length }}）</summary>
            <ul
              ><li v-for="(line, index) in analysis.analysis.evidence" :key="index">{{
                line
              }}</li></ul
            >
          </details>
        </template>
      </section>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { ref, watch, onBeforeUnmount, onDeactivated } from 'vue'
  import { getApiCaseDiagnosisPreview, postApiCaseDiagnosis } from '@/api/system/execution_result'
  import type {
    ApiCaseDiagnosisPreview,
    ApiCaseDiagnosisResult,
  } from '@/api/system/execution_result'

  const props = defineProps<{ resultId?: number | string | null }>()
  const visible = ref(false)
  const previewLoading = ref(false)
  const analysisLoading = ref(false)
  const previewError = ref('')
  const preview = ref<ApiCaseDiagnosisPreview | null>(null)
  const analysis = ref<ApiCaseDiagnosisResult | null>(null)
  const focusIndex = ref(0)
  const scope = ref<'auto' | 'focus' | 'all'>('auto')
  let sequence = 0
  let analysisSequence = 0

  function open() {
    visible.value = true
    void loadPreview()
  }

  async function loadPreview() {
    const token = ++sequence
    preview.value = null
    analysis.value = null
    previewError.value = ''
    analysisSequence++
    analysisLoading.value = false
    previewLoading.value = false
    if (!props.resultId) return
    previewLoading.value = true
    try {
      const response = await getApiCaseDiagnosisPreview(props.resultId)
      if (token !== sequence) return
      preview.value = response.data
      focusIndex.value = response.data.units.find((unit) => unit.status === 0)?.unit_index ?? 0
      scope.value = 'auto'
    } catch (loadFailure0) {
      if (token === sequence) (reportLoadError(loadFailure0, "执行结果加载失败，请稍后重试。", false), previewError.value = '执行结果加载失败，请稍后重试。')
    } finally {
      if (token === sequence) previewLoading.value = false
    }
  }

  function selectUnit(index: number) {
    analysisSequence++
    analysisLoading.value = false
    focusIndex.value = index
    scope.value = 'focus'
    analysis.value = null
  }

  async function analyze() {
    if (!props.resultId || !preview.value?.can_analyze || analysisLoading.value) return
    const token = sequence,
      analysisToken = ++analysisSequence
    const evidenceLevel = preview.value.evidence_level
    const isCurrent = () =>
      token === sequence && analysisToken === analysisSequence && visible.value
    analysisLoading.value = true
    analysis.value = null
    try {
      const response = await postApiCaseDiagnosis({
        result_id: props.resultId,
        scope: scope.value,
        focus_index: focusIndex.value,
      })
      if (isCurrent()) analysis.value = response.data
    } catch {
      if (isCurrent()) {
        analysis.value = {
          available: false,
          reason: 'AI 分析暂时不可用，请稍后重试',
          result_id: Number(props.resultId),
          scope_used: scope.value,
          included_unit_count: 0,
          omitted_unit_count: 0,
          evidence_level: evidenceLevel,
          focus_index: focusIndex.value,
        }
      }
    } finally {
      if (isCurrent()) analysisLoading.value = false
    }
  }

  watch(
    () => props.resultId,
    () => {
      sequence += 1
      analysisSequence++
      analysisLoading.value = false
      previewLoading.value = false
      analysis.value = null
      preview.value = null
      if (visible.value) void loadPreview()
    }
  )

  function close() {
    sequence++
    analysisSequence++
    visible.value = false
    analysisLoading.value = false
    previewLoading.value = false
  }
  watch(visible, (value) => {
    if (!value) close()
  })
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>

<style scoped>
  .mango-case-diagnosis {
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    color: var(--m-text);
  }
  .mango-case-diagnosis__preview {
    min-height: 80px;
  }
  .mango-case-diagnosis__steps,
  .mango-case-diagnosis__result {
    padding: 14px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }
  .mango-case-diagnosis__result {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .mango-case-diagnosis__result p {
    margin: 0;
    overflow-wrap: anywhere;
  }
  .mango-case-diagnosis__notice {
    color: var(--m-muted);
  }
  .mango-case-diagnosis__steps h3,
  .mango-case-diagnosis__result h3 {
    margin: 0 0 12px;
    font-size: 14px;
    font-weight: 600;
  }
  .mango-case-diagnosis__step-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    max-height: 360px;
    overflow-y: auto;
    padding: 2px;
  }
  .mango-case-diagnosis__step {
    width: 100%;
    min-width: 0;
    min-height: 48px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    color: var(--m-text);
    background: var(--m-surface);
    text-align: left;
    cursor: pointer;
    transition: border-color 150ms ease, background-color 150ms ease;
  }
  .mango-case-diagnosis__step:hover {
    background: var(--m-surface-soft);
    border-color: var(--m-border-strong);
  }
  .mango-case-diagnosis__step.is-selected {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 6%, var(--m-surface));
    box-shadow: inset 3px 0 var(--m-primary);
  }
  .mango-case-diagnosis__step:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 1px;
  }
  .mango-case-diagnosis__step-index {
    flex: none;
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--m-radius-sm);
    color: var(--m-text-2);
    background: var(--m-surface-soft);
    font-size: 12px;
    font-weight: 600;
  }
  .mango-case-diagnosis__step.is-selected .mango-case-diagnosis__step-index {
    color: var(--m-primary);
    background: var(--m-surface);
  }
  .mango-case-diagnosis__step-main {
    flex: 1;
    min-width: 0;
  }
  .mango-case-diagnosis__step-main strong {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-case-diagnosis__step-status {
    flex: none;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
  }
  .mango-case-diagnosis__step-status::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }
  .mango-case-diagnosis__step-status--pass {
    color: var(--m-success);
  }
  .mango-case-diagnosis__step-status--fail {
    color: var(--m-danger);
  }
  .mango-case-diagnosis__step-status--other {
    color: var(--m-warning);
  }
  .mango-case-diagnosis__actions {
    display: flex;
    justify-content: flex-end;
    padding-top: 12px;
    margin-top: 12px;
    border-top: 1px solid var(--m-border);
  }
  .mango-case-diagnosis__location {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--m-border);
  }
  .mango-case-diagnosis__location span {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-case-diagnosis__finding {
    padding: 10px 12px;
    border-left: 3px solid var(--m-danger);
    border-radius: var(--m-radius-sm);
    background: color-mix(in srgb, var(--m-danger) 5%, var(--m-surface));
  }
  .mango-case-diagnosis__finding strong,
  .mango-case-diagnosis__next-check strong {
    display: block;
    margin-bottom: 6px;
    font-size: 12px;
  }
  .mango-case-diagnosis__finding p {
    font-weight: 500;
  }
  .mango-case-diagnosis__next-check {
    padding: 10px 12px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }
  .mango-case-diagnosis__evidence {
    border-top: 1px solid var(--m-border);
    padding-top: 10px;
  }
  .mango-case-diagnosis__evidence summary {
    width: fit-content;
    color: var(--m-text-2);
    cursor: pointer;
  }
  .mango-case-diagnosis__evidence ul {
    margin: 8px 0 0;
    padding-left: 20px;
    color: var(--m-text-2);
  }
  .mango-case-diagnosis__evidence li + li {
    margin-top: 4px;
  }
  @media (max-width: 760px) {
    .mango-case-diagnosis__step-list {
      grid-template-columns: 1fr;
    }
  }
</style>
