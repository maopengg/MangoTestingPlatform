<template>
  <section class="mango-assertion-result">
    <div class="mango-assertion-result__heading">
      <div class="mango-assertion-result__heading-text">
        <h3>断言结果</h3>
        <p>同组按且/或判断，组间均需通过；或组中单条失败不代表整组失败。</p>
      </div>
      <div class="mango-assertion-result__actions">
        <a-button v-if="failedCount" size="small" type="outline" :aria-pressed="onlyFailed" @click="onlyFailed = !onlyFailed">
          {{ onlyFailed ? '查看全部' : '只看失败' }}
        </a-button>
        <AssertionAiAnalysis :data="assertionData" />
      </div>
    </div>
    <p v-if="stale" class="mango-assertion-result__stale">
      配置或环境已变化，以下是修改前的验证结果；请重新验证。
    </p>
    <div v-if="!assertionData.length" class="mango-empty-placeholder">暂无断言结果</div>
    <div v-else class="mango-assertion-grid-viewport mango-native-scrollbar">
      <div class="mango-assertion-grid" aria-label="断言结果">
        <div class="mango-assertion-grid__row mango-assertion-grid__header">
          <span>断言组</span>
          <span>组内关系</span>
          <span>提取方法</span>
          <span>实际值（响应值）</span>
          <span>断言方法</span>
          <span>预期值</span>
          <span>结果</span>
        </div>
        <div
          v-for="(item, index) in visibleAssertions"
          :key="index"
          class="mango-assertion-grid__row mango-assertion-grid__item"
          :class="item.status === 1 ? 'mango-assertion-grid__item--pass' : 'mango-assertion-grid__item--fail'"
        >
          <div class="mango-assertion-grid__cell mango-assertion-grid__group" :data-group-tone="groupTones.get(item.group_name?.trim() || '')">
            <a-tooltip :content="getGroupNameText(item)" mini>
              <span class="mango-assertion-grid__ellipsis">{{ getGroupNameText(item) }}</span>
            </a-tooltip>
          </div>
          <div class="mango-assertion-grid__cell mango-assertion-grid__group" :data-group-tone="groupTones.get(item.group_name?.trim() || '')">{{ getGroupLogicText(item) }}</div>
          <div class="mango-assertion-grid__cell mango-assertion-grid__source">
            <span class="mango-assertion-grid__primary">{{ getSourceTypeText(item.source_type) }}</span>
            <a-tooltip v-if="hasActualSource(item)" :content="formatTooltipValue(item.actual_source)" mini>
              <span class="mango-assertion-grid__secondary">{{ formatDisplayValue(item.actual_source) }}</span>
            </a-tooltip>
          </div>
          <div class="mango-assertion-grid__cell mango-assertion-grid__value">
            <a-tooltip :content="formatTooltipValue(item.actual)" mini>
              <span class="mango-assertion-grid__ellipsis">{{ formatDisplayValue(item.actual) }}</span>
            </a-tooltip>
          </div>
          <div class="mango-assertion-grid__cell mango-assertion-grid__method">
            <a-tooltip :content="item.method || '—'" mini>
              <span class="mango-assertion-grid__ellipsis">{{ item.method || '—' }}</span>
            </a-tooltip>
          </div>
          <div class="mango-assertion-grid__cell mango-assertion-grid__value">
            <a-tooltip :content="getExpectedDisplayValue(item)" mini>
              <span class="mango-assertion-grid__ellipsis">{{ formatDisplayValue(item.expect) }}</span>
            </a-tooltip>
            <a-tooltip v-if="hasExpectedSource(item)" :content="formatTooltipValue(item.expect_source)" mini>
              <span class="mango-assertion-grid__secondary">来源：{{ formatDisplayValue(item.expect_source) }}</span>
            </a-tooltip>
          </div>
          <div class="mango-assertion-grid__cell mango-assertion-grid__status"
            :aria-label="item.status === 1 ? '断言通过' : '断言失败'">
            <a-tooltip :content="getResultSentence(item)" mini>
              <span
                class="mango-assertion-grid__description mango-assertion-grid__ellipsis"
                :class="{ 'mango-assertion-grid__description--pass': item.status === 1 }"
              >{{ getResultSentence(item) }}</span>
            </a-tooltip>
            <a-tooltip v-if="item.status !== 1 && item.ass_msg?.trim()" :content="item.ass_msg" mini>
              <span class="mango-assertion-grid__raw-error mango-assertion-grid__ellipsis">原始错误：{{ item.ass_msg }}</span>
            </a-tooltip>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import AssertionAiAnalysis from './AssertionAiAnalysis.vue'

  interface AssertionItem {
    actual: unknown
    expect: unknown
    method: string
    ass_msg: string
    status: number
    group_name?: string | null
    group_logic?: string | null
    source_type?: string | null
    actual_source?: unknown
    expect_source?: unknown
  }

  const props = defineProps<{ data?: AssertionItem[] | null; stale?: boolean }>()
  const enumStore = useEnum()
  const assertionData = computed(() => Array.isArray(props.data)
    ? props.data.filter(item => item.source_type !== 'assertion_group') : [])
  const groupTones = computed(() => {
    const tones = new Map<string, number>()
    for (const item of assertionData.value) {
      const name = item.group_name?.trim()
      if (name && !tones.has(name)) tones.set(name, tones.size % 6)
    }
    return tones
  })
  const onlyFailed = ref(false)
  const failedCount = computed(() => assertionData.value.filter(item => Number(item.status) === 0).length)
  const visibleAssertions = computed(() => {
    if (!onlyFailed.value) return assertionData.value
    return assertionData.value.filter(item => Number(item.status) === 0)
  })
  watch(failedCount, count => { if (!count) onlyFailed.value = false })
  const displayValueMaxLength = computed(() => {
    const value = Number(enumStore.assertion_result_display_max_length)
    return Number.isInteger(value) && value > 0 ? value : 1000
  })

  function truncateDisplayText(text: string) {
    const maxLength = displayValueMaxLength.value
    return text.length > maxLength ? `${text.slice(0, maxLength)}…（已截断，共${text.length}字符）` : text
  }

  function formatCopyValue(value: unknown): string {
    if (value === undefined) return ''
    if (value === null) return 'null'
    if (typeof value === 'object') {
      try { return JSON.stringify(value) ?? String(value) } catch { return String(value) }
    }
    return String(value)
  }

  function formatDisplayValue(value: unknown) {
    if (value === undefined) return '未提供'
    return truncateDisplayText(formatCopyValue(value))
  }

  function formatTooltipValue(value: unknown) {
    const text = value === undefined ? '未提供' : formatCopyValue(value)
    return text.length > 2000 ? `${text.slice(0, 2000)}…` : text
  }

  function getFailureDescription(item: AssertionItem) {
    if (item.status === 1) return '—'
    const message = String(item.ass_msg || '')
    if (!message) return '断言未通过，未提供失败说明'
    const match = message.match(/(?:断言失败原因|执行异常|原因|错误)[:：]([^；\n]+)/)
    return truncateDisplayText((match?.[1] || message).trim())
  }

  function getResultSentence(item: AssertionItem) {
    if (item.source_type === 'assertion_group') return item.ass_msg || '断言组汇总'
    const passed = Number(item.status) === 1
    const method = String(item.method || '断言').trim()
    const message = String(item.ass_msg || '')
    if (!passed && (item.actual === undefined || /提取失败|执行异常|配置错误/.test(message))) {
      return getFailureDescription(item)
    }

    const actual = formatTooltipValue(item.actual)
    const expected = formatTooltipValue(item.expect)
    const actualText = `实际值（${actual}）`
    const expectedText = `预期值（${expected}）`

    if (method === '等于预期值' || method === 'p_is_equal_to') {
      return `${actualText}${passed ? '等于' : '不等于'}${expectedText}`
    }
    if (method === '不等于预期值' || method === 'p_is_not_equal_to') {
      return `${actualText}${passed ? '不等于' : '等于'}${expectedText}`
    }
    if (method === '不是null' || method === 'p_is_not_none') {
      return `${actualText}${passed ? '不为' : '为'} null`
    }
    if (method === '是null' || method === 'p_is_none') {
      return `${actualText}${passed ? '为' : '不为'} null`
    }
    if (method === '是False' || method === '是True') {
      return `${actualText}${passed ? '是' : '不是'} ${method.slice(1)}`
    }
    return passed ? `满足“${method}”条件` : `未满足“${method}”条件，具体值见左侧`
  }

  function isResponseFieldAssertion(item: AssertionItem) {
    return ['jsonpath', 'regex', 'cache'].includes(String(item.source_type || '').toLowerCase())
  }

  function getGroupNameText(item: AssertionItem) {
    const name = String(item.group_name || '').trim()
    return name || (isResponseFieldAssertion(item) ? '未分组' : '—')
  }

  function getGroupLogicText(item: AssertionItem) {
    if (!item.group_name && !isResponseFieldAssertion(item)) return '—'
    return String(item.group_logic || 'AND').toUpperCase() === 'OR' ? '或' : '且'
  }

  function getSourceTypeText(sourceType?: string | null) {
    const sourceMap: Record<string, string> = {
      jsonpath: 'JSONPath', regex: '正则表达式', cache: '缓存值',
      general: '直接取值', json_all: '响应 JSON', text_all: '响应文本',
      schema: '响应结构', sql: 'SQL 查询', assertion_group: '组汇总',
    }
    return sourceType ? sourceMap[sourceType] || sourceType : '直接取值'
  }

  function hasActualSource(item: AssertionItem) {
    return item.actual_source !== undefined && item.actual_source !== null && item.actual_source !== ''
  }

  function sortJsonValue(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(sortJsonValue)
    if (value && typeof value === 'object') {
      return Object.fromEntries(
        Object.entries(value).sort(([left], [right]) => left.localeCompare(right))
          .map(([key, entry]) => [key, sortJsonValue(entry)])
      )
    }
    return value
  }

  function comparableExpectedValue(value: unknown) {
    const text = formatCopyValue(value)
    if (typeof value === 'string' && !/^\s*[\[{]/.test(value)) return text
    try {
      const parsed = typeof value === 'string' ? JSON.parse(value) : value
      if (parsed && typeof parsed === 'object') return JSON.stringify(sortJsonValue(parsed))
    } catch {
      // 非 JSON 文本保持原样比较。
    }
    return text
  }

  function hasExpectedSource(item: AssertionItem) {
    return item.expect_source !== undefined && item.expect_source !== null && item.expect_source !== ''
      && comparableExpectedValue(item.expect_source) !== comparableExpectedValue(item.expect)
  }

  function getExpectedDisplayValue(item: AssertionItem) {
    const expected = formatTooltipValue(item.expect)
    return hasExpectedSource(item) ? `${expected}（来源：${formatTooltipValue(item.expect_source)}）` : expected
  }

</script>

<style scoped>
  .mango-assertion-result { min-width: 0; }
  .mango-assertion-result__heading { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--m-border); }
  .mango-assertion-result__heading-text { min-width: 0; }
  .mango-assertion-result__heading-text h3 { margin: 0; color: var(--m-text); font-size: 14px; font-weight: 600; }
  .mango-assertion-result__heading-text p { margin: 4px 0 0; color: var(--m-muted); font-size: 12px; }
  .mango-assertion-result__actions { display: flex; flex: none; align-items: center; gap: 8px; }
  .mango-assertion-result__stale { margin: 0 0 10px; color: var(--m-warning); font-size: 12px; }
  .mango-empty-placeholder { text-align: center; color: var(--m-muted); font-size: 14px; padding: 20px; background: var(--m-surface-soft); border: 1px dashed var(--m-border); border-radius: var(--m-radius-md); }
  .mango-assertion-grid-viewport { width: 100%; overflow-x: auto; }
  .mango-assertion-grid { min-width: 1120px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); overflow: hidden; }
  .mango-assertion-grid__row { display: grid; grid-template-columns: 112px 76px 128px minmax(120px, 1fr) 140px minmax(120px, 1fr) minmax(220px, 1.5fr); align-items: center; }
  .mango-assertion-grid__row > * { min-width: 0; padding: 8px 10px; }
  .mango-assertion-grid__header { background: var(--m-surface-soft); color: var(--m-text-2); font-size: 12px; font-weight: 600; white-space: nowrap; border-bottom: 1px solid var(--m-border); }
  .mango-assertion-grid__item { background: var(--m-surface); border-bottom: 1px solid var(--m-border); font-size: 12px; min-height: 48px; }
  .mango-assertion-grid__item:last-child { border-bottom: 0; }
  .mango-assertion-grid__item--pass { background: color-mix(in srgb, var(--m-success) 6%, var(--m-surface)); }
  .mango-assertion-grid__item--fail { background: color-mix(in srgb, var(--m-danger) 6%, var(--m-surface)); }
  .mango-assertion-grid__item--pass:hover { background: color-mix(in srgb, var(--m-success) 10%, var(--m-surface)); }
  .mango-assertion-grid__item--fail:hover { background: color-mix(in srgb, var(--m-danger) 10%, var(--m-surface)); }
  .mango-assertion-grid__status { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
  .mango-assertion-grid__description { max-width: 100%; color: var(--m-danger); font-size: 11px; font-weight: 600; }
  .mango-assertion-grid__description--pass { color: var(--m-text-2); font-weight: 400; }
  .mango-assertion-grid__raw-error { max-width: 100%; color: var(--m-muted); font-size: 11px; }
  .mango-assertion-grid__cell { min-width: 0; overflow: hidden; }
  .mango-assertion-grid__group {
    align-self: stretch;
    display: flex;
    align-items: center;
    background: var(--m-surface-soft);
    color: var(--m-text-2);
  }
  .mango-assertion-grid__group[data-group-tone='0'] { background: color-mix(in srgb, var(--m-primary) 12%, var(--m-surface)); }
  .mango-assertion-grid__group[data-group-tone='1'] { background: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface)); }
  .mango-assertion-grid__group[data-group-tone='2'] { background: color-mix(in srgb, var(--m-chart-5) 16%, var(--m-surface)); }
  .mango-assertion-grid__group[data-group-tone='3'] { background: color-mix(in srgb, var(--m-primary) 22%, var(--m-surface)); }
  .mango-assertion-grid__group[data-group-tone='4'] { background: color-mix(in srgb, var(--m-warning) 22%, var(--m-surface)); }
  .mango-assertion-grid__group[data-group-tone='5'] { background: color-mix(in srgb, var(--m-chart-5) 28%, var(--m-surface)); }
  .mango-assertion-grid__primary, .mango-assertion-grid__secondary, .mango-assertion-grid__ellipsis { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-assertion-grid__primary { color: var(--m-text); font-weight: 500; }
  .mango-assertion-grid__secondary { margin-top: 2px; color: var(--m-muted); font-size: 11px; }
  .mango-assertion-grid__value { display: flex; flex-direction: column; gap: 2px; }
  .mango-assertion-grid__value .mango-assertion-grid__ellipsis { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  .mango-assertion-grid__method .mango-assertion-grid__ellipsis { font-weight: 500; }
</style>
