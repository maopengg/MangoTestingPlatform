<template>
  <div class="mango-ui-step-runtime" :class="{ 'mango-ui-step-runtime--frameless': frameless }">
    <div v-if="showHeader" class="mango-ui-step-runtime__head">
      <span>{{ title }}</span>
      <a-tag size="small" :color="statusColor">
        {{ statusText }}
      </a-tag>
    </div>

    <div v-if="hasResult" class="mango-ui-step-runtime__body">
      <div class="mango-ui-step-runtime__grid">
        <div>
          <span>执行方法</span>
          <strong>{{ operationLabel }}</strong>
        </div>
        <div>
          <span>等待时间</span>
          <strong>{{ formatSleep(result?.sleep) }}</strong>
        </div>
        <div v-if="result?.duration_ms !== undefined && result?.duration_ms !== null">
          <span>执行耗时</span>
          <strong>{{ formatDuration(result.duration_ms) }}</strong>
        </div>
        <div>
          <span>结果项</span>
          <strong>{{ resultElementRows.length }}</strong>
        </div>
        <div v-if="matchCountSummary !== '-'">
          <span>匹配数量</span>
          <strong>{{ matchCountSummary }}</strong>
        </div>
        <div v-if="result?.page_title">
          <span>页面标题</span>
          <a-tooltip :content="result.page_title">
            <strong>{{ result.page_title }}</strong>
          </a-tooltip>
        </div>
        <div v-if="result?.viewport">
          <span>视口</span>
          <strong>{{ formatViewport(result.viewport) }}</strong>
        </div>
        <div v-if="locatorEngineSummary">
          <span>定位引擎</span>
          <a-tooltip :content="locatorEngineSummary">
            <strong>{{ locatorEngineSummary }}</strong>
          </a-tooltip>
        </div>
        <div v-if="result?.page_url" class="mango-ui-step-runtime__wide">
          <span>页面地址</span>
          <a-tooltip :content="result.page_url">
            <strong>{{ result.page_url }}</strong>
          </a-tooltip>
        </div>
        <div v-if="result?.error_message" class="mango-ui-step-runtime__wide">
          <span>错误提示</span>
          <a-tooltip :content="result.error_message">
            <strong class="mango-ui-step-runtime__error">{{ result.error_message }}</strong>
          </a-tooltip>
        </div>
        <div v-if="result?.ass_msg" class="mango-ui-step-runtime__wide">
          <span>断言提示</span>
          <a-tooltip :content="result.ass_msg">
            <strong>{{ result.ass_msg }}</strong>
          </a-tooltip>
        </div>
      </div>

      <div v-if="elementRows.length" class="mango-ui-step-runtime__elements">
        <article
          v-for="(element, index) in elementRows"
          :key="`${index}-${element.id ?? element.name}`"
          class="mango-ui-step-runtime__element-card"
        >
          <div class="mango-ui-step-runtime__element-head">
            <strong>{{ getElementTitle(element, index) }}</strong>
            <div class="mango-ui-step-runtime__element-tags">
              <a-tag
                v-if="element.visible !== null && element.visible !== undefined"
                size="small"
                :color="element.visible ? 'green' : 'red'"
              >
                {{ element.visible ? '可见' : '不可见' }}
              </a-tag>
              <a-tag
                v-if="element.enabled !== null && element.enabled !== undefined"
                size="small"
                :color="element.enabled ? 'green' : 'red'"
              >
                {{ element.enabled ? '启用' : '禁用' }}
              </a-tag>
              <a-tag
                v-if="element.editable !== null && element.editable !== undefined"
                size="small"
                :color="element.editable ? 'green' : 'gray'"
              >
                {{ element.editable ? '可编辑' : '不可编辑' }}
              </a-tag>
              <a-tag v-if="element.__configuredFallback" size="small" color="gray">
                配置定位
              </a-tag>
              <a-tag v-else size="small" color="arcoblue">
                匹配 {{ element.ele_quantity ?? '-' }}
              </a-tag>
              <a-tag
                v-if="
                  element.locate_duration_ms !== undefined && element.locate_duration_ms !== null
                "
                size="small"
                color="gray"
              >
                {{ formatDuration(element.locate_duration_ms) }}
              </a-tag>
            </div>
          </div>
          <div class="mango-ui-step-runtime__row mango-ui-step-runtime__row--locators">
            <span>定位表达式</span>
            <div class="mango-ui-step-runtime__locator-list">
              <div
                v-for="(locator, locatorIndex) in getElementLocatorRows(element)"
                :key="`${locator.loc}-${locatorIndex}`"
                class="mango-ui-step-runtime__locator-item"
              >
                <span class="mango-ui-step-runtime__locator-type">
                  {{ locator.expText }}
                </span>
                <a-tooltip :content="locator.loc">
                  <strong>{{ locator.loc }}</strong>
                </a-tooltip>
                <span
                  v-if="locator.sub !== undefined && locator.sub !== null"
                  class="mango-ui-step-runtime__locator-sub"
                >
                  下标 {{ locator.sub }}
                </span>
              </div>
            </div>
          </div>
          <div v-if="element.bounding_box" class="mango-ui-step-runtime__row">
            <span>元素位置</span>
            <strong>{{ formatBoundingBox(element.bounding_box) }}</strong>
          </div>
          <div
            v-if="getTextSnippets(element).length"
            class="mango-ui-step-runtime__row mango-ui-step-runtime__row--text"
          >
            <span>文本摘要</span>
            <div class="mango-ui-step-runtime__snippet-list">
              <a-tooltip
                v-for="(snippet, snippetIndex) in getTextSnippets(element)"
                :key="`${snippetIndex}-${snippet}`"
                :content="snippet"
              >
                <strong>{{ snippet }}</strong>
              </a-tooltip>
            </div>
          </div>
          <div
            v-if="element.element_text && !getTextSnippets(element).length"
            class="mango-ui-step-runtime__row"
          >
            <span>元素文本</span>
            <a-tooltip :content="element.element_text">
              <strong>{{ element.element_text }}</strong>
            </a-tooltip>
          </div>
        </article>
      </div>

      <div v-if="locatorCandidateRows.length" class="mango-ui-step-runtime__engine">
        <div class="mango-ui-step-runtime__shot-head">
          <span>定位候选</span>
          <strong>{{ locatorCandidateRows.length }} 项</strong>
        </div>
        <div class="mango-ui-step-runtime__candidate-list">
          <div
            v-for="(candidate, index) in locatorCandidateRows"
            :key="`${candidate.loc}-${index}`"
            class="mango-ui-step-runtime__candidate"
          >
            <a-tag size="small" :color="getCandidateStatus(candidate).color">
              {{ getCandidateStatus(candidate).text }}
            </a-tag>
            <span>{{ candidate.source || '-' }}</span>
            <a-tooltip :content="candidate.loc || '-'">
              <strong>{{ candidate.loc || '-' }}</strong>
            </a-tooltip>
            <em>匹配 {{ candidate.count ?? 0 }}</em>
            <em v-if="candidate.final_score !== null"> 评分 {{ candidate.final_score }} </em>
            <small
              v-if="candidate.reject_reason || candidate.decision_reasons?.length"
              :title="candidate.reject_reason || candidate.decision_reasons.join('；')"
            >
              {{ candidate.reject_reason || candidate.decision_reasons.join('；') }}
            </small>
          </div>
        </div>
      </div>

      <div v-if="pictureSrc" class="mango-ui-step-runtime__shot">
        <div class="mango-ui-step-runtime__shot-head">
          <span>{{ pictureTitle }}</span>
        </div>
        <a-image :src="pictureSrc" :width="imageWidth" fit="contain" />
      </div>
    </div>
    <div v-else class="mango-ui-step-runtime__empty">{{ emptyText }}</div>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import { useArtifactUrl } from '@/hooks/use-artifact-url'
  import { useEnum } from '@/store/modules/get-enum'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import { normalizeUiRuntime, uiFallbackElements, type UiElementView, type UiLocatorCandidate, type UiRuntimeView } from './ui-report'

  const props = withDefaults(defineProps<{
    result?: unknown
    fallbackOpeKey?: unknown
    fallbackElementName?: string
    fallbackElement?: unknown
    title?: string
    emptyText?: string
    imageWidth?: string | number
    pictureTitle?: string
    frameless?: boolean
    showHeader?: boolean
  }>(), {
    result: null, fallbackOpeKey: '', fallbackElementName: '', fallbackElement: null,
    title: '最近测试结果', emptyText: '暂无最近测试结果', imageWidth: '100%',
    pictureTitle: '失败截图', frameless: false, showHeader: true,
  })
  const enumStore = useEnum()
  const useSelectValue = useSelectValueStore()
  const result = computed(() => normalizeUiRuntime(props.result))
  const hasResult = computed(() => {
    const row = result.value
    return row !== null && (row.id !== null || row.page_step_details_id !== null || Boolean(row.ope_key) || row.status !== null)
  })
  const resultElementRows = computed(() => result.value?.elements ?? [])
  const elementRows = computed(() => resultElementRows.value.length ? resultElementRows.value : uiFallbackElements(props.fallbackElement))
  const statusText = computed(() => result.value?.status === 1 ? '通过' : result.value?.status === 0 ? '失败' : result.value?.status === 3 ? '执行中' : '未测试')
  const statusColor = computed(() => result.value?.status === 1 ? 'green' : result.value?.status === 0 ? 'red' : result.value?.status === 3 ? 'orange' : 'gray')
  const operationLabel = computed(() => {
    const value = result.value?.ope_key || (typeof props.fallbackOpeKey === 'string' ? props.fallbackOpeKey : '')
    if (!value) return '-'
    const label: unknown = useSelectValue.getSelectLabel(value)
    return typeof label === 'string' && label ? label : useSelectValue.findItemByValue(value)?.label || value
  })
  const picturePath = computed(() => result.value?.picture_path || '')
  const pictureSrc = useArtifactUrl(picturePath)
  const locatorEngineSummary = computed(() => {
    const engine = result.value?.locator_engine
    if (!engine) return ''
    return `${engine.used_source || '-'} / 候选 ${engine.candidate_count ?? 0} / ${engine.temporary_heal_used ? '已临时自愈' : '未临时自愈'}`
  })
  const locatorCandidateRows = computed(() => result.value?.locator_engine?.candidates ?? [])
  const matchCountSummary = computed(() => {
    const counts = resultElementRows.value.map(item => item.ele_quantity).filter((value): value is number => value !== null)
    return counts.length ? String(counts.reduce((total, value) => total + value, 0)) : '-'
  })
  function getCandidateStatus(candidate: UiLocatorCandidate) {
    if (!candidate.verified) return { text: '验证失败', color: 'red' }
    if (candidate.adopted || candidate.decision_status === 'temporary_heal' || candidate.decision_status === 'auto_apply') return { text: '已采用', color: 'green' }
    return { text: '已验证未采用', color: 'orange' }
  }
  function formatSleep(value: UiRuntimeView['sleep'] | undefined) {
    return value === null || value === undefined || value === '' ? '-' : `${value} 秒`
  }
  function formatDuration(value: number | null | undefined) {
    if (value == null) return '-'
    return value >= 1000 ? `${(value / 1000).toFixed(2)} 秒` : `${value} ms`
  }
  function formatViewport(value: UiRuntimeView['viewport']) {
    return value ? `${value.width ?? '-'} × ${value.height ?? '-'}` : '-'
  }
  function formatBoundingBox(value: UiElementView['bounding_box']) {
    return value ? `x:${value.x ?? '-'} y:${value.y ?? '-'} w:${value.width ?? '-'} h:${value.height ?? '-'}` : '-'
  }
  function getElementLocatorRows(element: UiElementView) {
    return element.locators.map(locator => ({
      ...locator, expText: enumStore.element_exp?.find(item => item.key === locator.exp)?.title ?? locator.exp ?? '-',
    }))
  }
  function getElementTitle(element: UiElementView, index: number) {
    return element.name || props.fallbackElementName || `元素 ${index + 1}`
  }
  function getTextSnippets(element: UiElementView) { return element.text_snippets }
</script>

<style scoped>
  .mango-ui-step-runtime {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: min(520px, 58vh);
    overflow: auto;
    padding: 8px;
    border-radius: 6px;
    background: var(--m-surface-soft);
  }

  .mango-ui-step-runtime--frameless {
    max-height: none;
    overflow: visible;
    padding: 0;
    background: transparent;
  }

  .mango-ui-step-runtime__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  .mango-ui-step-runtime__body {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mango-ui-step-runtime__grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
    gap: 6px;
  }

  .mango-ui-step-runtime__grid > div {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
    padding: 5px 8px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-ui-step-runtime__grid span,
  .mango-ui-step-runtime__row span,
  .mango-ui-step-runtime__shot-head span,
  .mango-ui-step-runtime__locator-sub {
    flex: 0 0 auto;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ui-step-runtime__row > span:first-child {
    width: 64px;
  }

  .mango-ui-step-runtime__grid strong,
  .mango-ui-step-runtime__row strong {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-step-runtime__wide {
    grid-column: 1 / -1;
  }

  .mango-ui-step-runtime__error {
    color: var(--m-danger) !important;
  }

  .mango-ui-step-runtime__elements {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 8px;
  }

  .mango-ui-step-runtime__engine {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px;
    border-radius: 6px;
    background: var(--m-surface-soft);
  }

  .mango-ui-step-runtime__candidate-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .mango-ui-step-runtime__candidate {
    display: grid;
    grid-template-columns: auto 120px minmax(0, 1fr) auto;
    align-items: center;
    gap: 6px;
    min-width: 0;
    padding: 5px 8px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-ui-step-runtime__candidate span,
  .mango-ui-step-runtime__candidate em {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    font-style: normal;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-step-runtime__candidate strong {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-step-runtime__candidate small {
    grid-column: 2 / -1;
    overflow: hidden;
    color: var(--m-danger);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-step-runtime__element-card {
    min-width: 0;
    padding: 8px;
    border-radius: 6px;
    background: var(--m-surface-soft);
  }

  .mango-ui-step-runtime__element-head,
  .mango-ui-step-runtime__row {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
  }

  .mango-ui-step-runtime__row {
    padding: 5px 8px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-ui-step-runtime__element-head {
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .mango-ui-step-runtime__element-tags {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    flex: 0 0 auto;
    gap: 4px;
  }

  .mango-ui-step-runtime__element-head strong {
    overflow: hidden;
    min-width: 0;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-step-runtime__row + .mango-ui-step-runtime__row {
    margin-top: 4px;
  }

  .mango-ui-step-runtime__row--locators {
    align-items: center;
  }

  .mango-ui-step-runtime__row--text {
    align-items: flex-start;
  }

  .mango-ui-step-runtime__locator-list {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-width: 0;
    gap: 4px;
  }

  .mango-ui-step-runtime__locator-item {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
  }

  .mango-ui-step-runtime__locator-type {
    max-width: 86px;
    padding: 1px 6px;
    color: var(--m-primary) !important;
    line-height: 18px;
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-primary-soft);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-step-runtime__locator-item strong {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-step-runtime__snippet-list {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-width: 0;
    gap: 4px;
  }

  .mango-ui-step-runtime__shot {
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
    padding: 8px;
    border-radius: 6px;
    background: var(--m-surface-soft);
  }

  .mango-ui-step-runtime__shot-head {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
  }

  .mango-ui-step-runtime__shot-head strong {
    overflow: hidden;
    min-width: 0;
    color: var(--m-text);
    font-size: 12px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ui-step-runtime__empty {
    padding: 18px 12px;
    color: var(--m-muted);
    font-size: 12px;
    text-align: center;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }
</style>
