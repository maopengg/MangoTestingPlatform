<template>
  <div class="mango-assertion-ai">
    <a-button size="small" type="outline" :disabled="!hasFailure"
      :title="hasFailure ? '打开断言 AI 分析' : '没有失败断言，无需 AI 分析'" @click="open">
      AI 分析
    </a-button>
    <a-drawer v-model:visible="visible" :width="'min(960px, 92vw)'"
      :footer="false" title="断言 AI 分析" class="mango-assertion-analysis-drawer" unmount-on-close @cancel="invalidateAnalysis">
      <div class="mango-assertion-analysis mango-native-scrollbar">
        <div class="mango-assertion-analysis__toolbar">
          <span>本次 {{ assertionData.length }} 条 · {{ failures.length }} 失败 · {{ passed.length }} 通过</span>
          <a-button size="small" :loading="loading" @click="analyze">重新分析</a-button>
        </div>
        <section class="mango-assertion-analysis__summary" aria-label="断言分析结论">
          <strong>为什么失败</strong>
          <p class="mango-assertion-analysis__conclusion">{{ deterministicSummary }}</p>
          <div v-if="analysis && !analysis.available" class="mango-assertion-analysis__notice" role="status">
            {{ analysis.reason }}；以下仍可查看真实断言结果。
          </div>
          <div v-else-if="analysis?.omitted_count" class="mango-assertion-analysis__notice" role="status">
            已分析 {{ analysis.analyzed_count }}/{{ failures.length }} 条失败断言，未覆盖项保留原始结果。
          </div>
        </section>
        <section aria-label="失败断言">
          <h3>失败断言（{{ failures.length }}）</h3>
          <article v-for="entry in failures" :key="entry.index" class="mango-assertion-analysis__item">
            <div class="mango-assertion-analysis__item-head">
              <strong>#{{ entry.index + 1 }} {{ entry.item.method || '断言' }}</strong>
              <a-tag color="red" size="small">失败</a-tag>
            </div>
            <div class="mango-assertion-analysis__target">
              <span>校验位置</span>
              <code>{{ sourceLabel(entry.item) || '当前断言的实际值' }}</code>
            </div>
            <p class="mango-assertion-analysis__cause">{{ failureReason(entry.item) }}</p>
            <div class="mango-assertion-analysis__comparison">
              <div><span>实际值 <small>{{ valueType(entry.item.actual) }}</small></span><code>{{ displayValue(entry.item.actual) }}</code></div>
              <div><span>预期值 <small>{{ valueType(entry.item.expect) }}</small></span><code>{{ displayValue(entry.item.expect) }}</code></div>
            </div>
            <div v-if="loading || analysisItem(entry.index)" class="mango-assertion-analysis__ai-note">
              <strong>AI 补充</strong>
              <p v-if="analysisItem(entry.index)">{{ analysisItem(entry.index)?.explanation }}</p>
              <p v-if="analysisItem(entry.index)?.next_check">建议检查：{{ analysisItem(entry.index)?.next_check }}</p>
              <p v-else-if="loading" class="mango-assertion-analysis__notice">正在分析…</p>
            </div>
            <a-collapse v-if="entry.item.ass_msg" :bordered="false">
              <a-collapse-item header="原始断言消息" :key="String(entry.index)">
                <pre class="mango-assertion-analysis__raw">{{ entry.item.ass_msg }}</pre>
              </a-collapse-item>
            </a-collapse>
          </article>
        </section>
        <a-collapse v-if="passed.length" :bordered="false" class="mango-assertion-analysis__passed">
          <a-collapse-item :header="`已通过断言 ${passed.length} 条`" key="passed">
            <div v-for="entry in passed" :key="entry.index" class="mango-assertion-analysis__passed-row">
              <span>#{{ entry.index + 1 }} {{ entry.item.method || '断言' }}</span>
              <span>{{ sourceLabel(entry.item) }}</span>
              <a-tag color="green" size="small">通过</a-tag>
            </div>
          </a-collapse-item>
        </a-collapse>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { postAssertionAiAnalysis } from '@/api/system/execution_result'
  import type { AssertionAiAnalysisResult } from '@/api/system/execution_result'

  interface AssertionItem {
    actual?: unknown
    expect?: unknown
    method?: string | null
    ass_msg?: string | null
    status?: number | string
    source_type?: string | null
    actual_source?: unknown
  }
  const props = defineProps<{ data?: AssertionItem[] | null }>()
  const visible = ref(false)
  const loading = ref(false)
  const analysis = ref<AssertionAiAnalysisResult | null>(null)
  let requestSequence = 0
  let active = true
  const route = useRoute()
  const user = useUserStore()
  const contextKey = computed(() => JSON.stringify([
    route.fullPath, user.userId, user.roleId, user.token, user.selected_environment,
  ]))
  const assertionData = computed(() => Array.isArray(props.data) ? props.data : [])
  const failures = computed(() => assertionData.value.flatMap((item, index) =>
    item && Number(item.status) === 0 ? [{ item, index }] : []))
  const passed = computed(() => assertionData.value.flatMap((item, index) =>
    item && Number(item.status) === 1 ? [{ item, index }] : []))
  const hasFailure = computed(() => failures.value.length > 0)
  const deterministicSummary = computed(() => {
    if (!failures.value.length) return '本次没有失败断言。'
    const first = failures.value[0]
    const location = sourceLabel(first.item)
    const target = location ? `第 ${first.index + 1} 条断言（${location}）` : `第 ${first.index + 1} 条断言`
    const more = failures.value.length > 1 ? `；另有 ${failures.value.length - 1} 条失败，见下方` : ''
    return `${target}：${failureReason(first.item).replace(/[。；.!?]+$/, '')}${more}。`
  })

  function invalidateAnalysis() {
    requestSequence += 1
    visible.value = false
    analysis.value = null
  }
  watch(() => props.data, invalidateAnalysis, { deep: true, flush: 'sync' })
  watch(contextKey, invalidateAnalysis, { flush: 'sync' })
  onDeactivated(() => { active = false; invalidateAnalysis() })
  onBeforeUnmount(() => { active = false; invalidateAnalysis() })
  onActivated(() => { active = true })

  function open() {
    if (!active || !hasFailure.value) return
    visible.value = true
    void analyze()
  }

  async function analyze() {
    if (!active || !visible.value || !hasFailure.value || loading.value) return
    const sequence = ++requestSequence
    const context = contextKey.value
    const current = () => active && visible.value && sequence === requestSequence && context === contextKey.value
    loading.value = true
    analysis.value = null
    try {
      const snapshot = cloneLosslessJson(assertionData.value.map(item => ({ ...item })))
      const response = await postAssertionAiAnalysis(snapshot)
      if (response.code !== 200 || !response.data) throw new Error('Invalid analysis response')
      if (current()) analysis.value = response.data
    } catch {
      if (current()) {
        analysis.value = { available: false, reason: 'AI 分析暂时不可用，请稍后重试',
          summary: '', failed_count: failures.value.length, analyzed_count: 0,
          omitted_count: failures.value.length, items: [] }
      }
    } finally {
      loading.value = false
    }
  }

  function analysisItem(index: number) {
    return analysis.value?.items?.find((item) => item.assertion_index === index)
  }

  function displayValue(value: unknown) {
    if (value === undefined) return '未提供（undefined）'
    if (value === null) return 'null'
    const text = typeof value === 'string' ? value : (JSON.stringify(value) ?? String(value))
    return text.length > 1000 ? `${text.slice(0, 1000)}…（页面仅展示前 1000 字符）` : text
  }

  function sourceLabel(item: AssertionItem) {
    if (typeof item.actual_source === 'string' && item.actual_source.trim()) return item.actual_source
    const sourceNames: Record<string, string> = {
      json_all: '响应 JSON', text_all: '响应文本', sql: 'SQL 查询结果',
      schema: '响应结构', cache: '运行缓存', jsonpath: 'JSONPath 提取结果',
    }
    return sourceNames[String(item.source_type || '')] || ''
  }

  function valueType(value: unknown) {
    if (value === undefined) return '未提供'
    if (value === null) return 'null'
    if (Array.isArray(value)) return '数组'
    return ({ string: '字符串', number: '数字', boolean: '布尔值', object: '对象' } as Record<string, string>)[typeof value] || typeof value
  }

  function failureReason(item: AssertionItem) {
    const method = String(item.method || '')
    if (item.actual === undefined) return '未取得实际值，无法满足当前断言；请检查字段路径或前置提取。'
    if (/不是.?null|不为.?null|not.?null|not.?none/i.test(method) && item.actual === null) {
      return '实际值为 null，但该断言要求它不是 null。'
    }
    const isEquality = /等于|相等|equal|equals/i.test(method) && !/不等|不相等|not.?equal/i.test(method)
    if (isEquality && item.actual === null && item.expect !== null) return '实际值为 null，预期值不是 null。'
    if (isEquality && valueType(item.actual) !== valueType(item.expect) && item.expect !== undefined) {
      return `值的类型不同：实际是${valueType(item.actual)}，预期是${valueType(item.expect)}。`
    }
    if (isEquality && typeof item.actual === 'string' && typeof item.expect === 'string') {
      const actual = item.actual
      const expected = item.expect
      if (actual === expected) return '显示值相同，但断言未通过；请展开原始消息检查比较规则或执行异常。'
      if (expected.startsWith(actual)) {
        return `字符串比较未通过：实际值比预期值少了末尾「${shortDifference(expected.slice(actual.length))}」。`
      }
      if (actual.startsWith(expected)) {
        return `字符串比较未通过：实际值比预期值多了末尾「${shortDifference(actual.slice(expected.length))}」。`
      }
      const actualChars = Array.from(actual)
      const expectedChars = Array.from(expected)
      const position = actualChars.findIndex((character, index) => character !== expectedChars[index])
      if (position >= 0 && position < 80) {
        return `字符串比较未通过：从第 ${position + 1} 个字符开始不同。`
      }
      return '字符串比较未通过：实际值与预期值不同。'
    }
    if (isEquality) return '实际值未达到“等于预期值”的条件，请核对下方两列和原始消息。'
    const detail = String(item.ass_msg || '').match(/(?:断言失败原因|执行异常|原因|错误)[:：]([^；\n]+)/)?.[1]?.trim()
    if (detail) return `未满足“${method || '当前'}”规则：${detail.slice(0, 160)}。`
    return `实际值未满足“${method || '当前'}”校验条件，请核对下方两列和原始消息。`
  }

  function shortDifference(value: string) {
    return value.length > 24 ? `${value.slice(0, 24)}…` : value
  }
</script>

<style scoped>
  .mango-assertion-analysis { height: 100%; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; color: var(--m-text); }
  .mango-assertion-analysis__toolbar, .mango-assertion-analysis__item-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .mango-assertion-analysis__summary, .mango-assertion-analysis__item { border: 1px solid var(--m-border); border-radius: 6px; padding: 12px; background: var(--m-surface); }
  .mango-assertion-analysis__summary p, .mango-assertion-analysis__item p { margin: 8px 0 0; overflow-wrap: anywhere; }
  .mango-assertion-analysis__conclusion { font-weight: 600; color: var(--m-danger); }
  .mango-assertion-analysis__notice { color: var(--m-muted); }
  .mango-assertion-analysis h3 { margin: 0 0 8px; font-size: 14px; }
  .mango-assertion-analysis__target { display: flex; align-items: baseline; gap: 8px; margin-top: 8px; overflow-wrap: anywhere; }
  .mango-assertion-analysis__target span { flex: none; color: var(--m-muted); }
  .mango-assertion-analysis__target code { font-weight: 600; }
  .mango-assertion-analysis__cause { padding: 8px 10px; border-left: 3px solid var(--m-danger); background: var(--m-surface-soft); font-weight: 600; }
  .mango-assertion-analysis__comparison { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }
  .mango-assertion-analysis__comparison > div { min-width: 0; padding: 8px; background: var(--m-surface-soft); }
  .mango-assertion-analysis__comparison span { display: block; margin-bottom: 4px; color: var(--m-muted); }
  .mango-assertion-analysis__comparison small { margin-left: 4px; }
  .mango-assertion-analysis__comparison code, .mango-assertion-analysis__raw { display: block; white-space: pre-wrap; overflow-wrap: anywhere; }
  .mango-assertion-analysis__ai-note { margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--m-border); }
  .mango-assertion-analysis__raw { max-height: 240px; overflow: auto; margin: 0; }
  .mango-assertion-analysis__passed-row { display: flex; align-items: center; gap: 12px; padding: 6px 0; border-bottom: 1px solid var(--m-border); }
  .mango-assertion-analysis__passed-row span:nth-child(2) { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  @media (max-width: 700px) { .mango-assertion-analysis__comparison { grid-template-columns: 1fr; } }
</style>
