<template>
  <div class="mango-item-result-content">
    <WorkflowResult v-if="item.details?.workflow?.length" :records="item.details.workflow" />
    <section v-if="item.details?.turns?.length" class="mango-item-result-section">
      <h3 class="mango-section-title">轮次结果</h3>
      <article v-for="turn in item.details.turns" :key="turn.index" class="mango-item-source">
        <div class="mango-item-source-heading"
          ><strong>{{ turn.name }}</strong
          ><span>{{ turn.scored ? `${turn.score ?? '—'} 分` : '不计分' }}</span></div
        >
        <JsonDisplay
          :data="{
            输入: turn.input,
            预期: turn.expected,
            实际输出: turn.output,
            结论: turn.verdict,
          }"
          :show-drawer-button="false"
        />
      </article>
    </section>
    <section class="mango-item-result-section">
      <h3 class="mango-section-title">输入</h3>
      <p v-if="question !== undefined" class="mango-item-result-text">{{
        question || '（空文本）'
      }}</p>
      <JsonDisplay v-else :data="item.item_snapshot?.input_data" :show-drawer-button="false" />
    </section>

    <div class="mango-item-answer-comparison">
      <section class="mango-item-result-section">
        <h3 class="mango-section-title">期望输出</h3>
        <p v-if="expectedAnswer !== undefined" class="mango-item-result-text">{{
          expectedAnswer || '（空文本）'
        }}</p>
        <JsonDisplay v-else :data="item.resolved_expected_output" :show-drawer-button="false" />
      </section>
      <section class="mango-item-result-section">
        <h3 class="mango-section-title">实际输出</h3>
        <p v-if="actualAnswer !== undefined" class="mango-item-result-text">{{
          actualAnswer || '（空文本）'
        }}</p>
        <p v-else-if="memories.length" class="mango-item-result-text"
          >检索返回
          {{ memories.length }} 条记忆，完整内容见下方“实际命中数据”。本次未生成问答答案。</p
        >
        <p v-else-if="item.execution_status !== 'success'" class="mango-item-result-text"
          >未获得有效输出</p
        >
        <JsonDisplay v-else :data="item.actual_output" :show-drawer-button="false" />
      </section>
    </div>

    <section v-if="expectedSources.length" class="mango-item-result-section">
      <h3 class="mango-section-title">{{
        actualAnswer !== undefined ? '评分依据' : '应命中的数据'
      }}</h3>
      <p class="mango-item-result-meta"
        >评测数据集：{{ datasetTitle }} · 条目 {{ item.dataset_item_id }}</p
      >
      <div v-for="(source, index) in expectedSources" :key="index" class="mango-item-source">
        <div class="mango-item-source-heading"
          ><strong
            >{{ actualAnswer !== undefined ? '原文材料' : '期望原文'
            }}<template v-if="expectedSources.length > 1"> {{ index + 1 }}</template></strong
          ><span v-if="source.time" class="mango-item-result-meta">{{ source.time }}</span></div
        >
        <p class="mango-item-result-text">{{ source.text }}</p>
        <p v-if="memories.length" class="mango-item-result-meta">{{
          source.ranks.length
            ? `召回位置：第 ${source.ranks.join('、')} 条`
            : '本次召回中未找到相同原文'
        }}</p>
      </div>
    </section>

    <section v-if="memories.length" class="mango-item-result-section">
      <h3 class="mango-section-title">实际命中数据 · {{ memories.length }} 条</h3>
      <ol class="mango-item-memory-list">
        <li v-for="(memory, index) in memories" :key="index" class="mango-item-source">
          <div class="mango-item-source-heading"
            ><strong>第 {{ index + 1 }} 条</strong
            ><span v-if="matchesExpected(memory)" class="mango-item-result-meta"
              >包含期望原文</span
            ></div
          >
          <p v-if="memoryContent(memory) !== undefined" class="mango-item-result-text">{{
            memoryContent(memory)
          }}</p>
          <JsonDisplay v-else :data="memory" />
          <div
            v-for="(source, sourceIndex) in memoryEvidence(memory)"
            :key="sourceIndex"
            class="mango-item-memory-evidence"
          >
            <span class="mango-item-result-meta"
              >来源原文<template v-if="source.occurredAt || source.occurred_at">
                · {{ source.occurredAt || source.occurred_at }}</template
              ></span
            >
            <p class="mango-item-result-text">{{ source.excerpt || '未返回来源原文' }}</p>
          </div>
        </li>
      </ol>
    </section>

    <section v-if="item.grades?.length" class="mango-item-result-section">
      <h3 class="mango-section-title">评分理由</h3>
      <div v-for="(grade, index) in item.grades" :key="index" class="mango-item-source">
        <div class="mango-item-source-heading"
          ><strong>{{
            memoryGraderNames[grade.grader_key]
              ? memoryGraderNames[grade.grader_key]
              : grade.grading_snapshot?.metric || grade.grader_key
          }}</strong
          ><a-tag size="small" :color="statusColor(grade.passed ? 'passed' : 'failed')">{{
            grade.score == null ? '未得出有效评分' : `${grade.score} 分`
          }}</a-tag
          ><span v-if="grade.raw_value?.classification">{{
            enumTitle('evaluation_answer_verdict', grade.raw_value.classification)
          }}</span></div
        >
        <p class="mango-item-result-text">{{ grade.reason || '未提供评分理由' }}</p>
        <dl v-if="grade.raw_value?.evidence" class="mango-item-judge-quotes">
          <div
            ><dt>实际答案引用</dt
            ><dd>{{ grade.raw_value.evidence.answer_quote || '（空文本）' }}</dd></div
          >
          <div
            ><dt>参考证据引用</dt
            ><dd>{{ grade.raw_value.evidence.reference_quote || '（空文本）' }}</dd></div
          >
        </dl>
        <template v-for="group in factCheckGroups" :key="group">
          <dl v-if="grade.raw_value?.[group]?.length" class="mango-item-judge-quotes">
            <div v-for="check in grade.raw_value[group]" :key="check.index">
              <dt
                >{{ group === 'expected_checks' ? '标准事实' : '实际输出' }} {{ check.index + 1 }} ·
                {{ enumTitle('evaluation_memory_fact_status', check.status) }}</dt
              >
              <dd>
                <p class="mango-item-result-text">{{ check.reason }}</p>
                <p v-if="check.actual_quote" class="mango-item-result-text"
                  >实际引用：{{ check.actual_quote }}</p
                >
                <p v-if="check.source_quote" class="mango-item-result-text"
                  >来源依据：{{ check.source_quote }}</p
                >
              </dd>
            </div>
          </dl>
        </template>
      </div>
    </section>
    <section class="mango-item-result-section">
      <a-tabs v-model:active-key="payloadTab" size="small">
        <a-tab-pane key="request" title="输入请求">
          <JsonDisplay :data="item.item_snapshot?.input_data" :show-drawer-button="false" />
        </a-tab-pane>
        <a-tab-pane key="response" title="响应 JSON">
          <JsonDisplay :data="item.actual_output" :show-drawer-button="false" />
        </a-tab-pane>
      </a-tabs>
    </section>
  </div>
</template>
<script setup lang="ts">
  import WorkflowResult from './WorkflowResult.vue'
  import { computed, ref, watch } from 'vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { useEvaluationEnums } from './useEvaluationEnums'
  import type { ItemResult } from '../types'
  import { resultObject, resultArray } from './result'
  const props = defineProps<{
    item: ItemResult
    dataset?: { id?: number; version_no?: number }
    datasetName?: string
  }>()
  const factCheckGroups = ['expected_checks', 'actual_checks'] as const
  const memoryGraderNames: Record<string, string> = {
    memory_qa: '记忆问答',
    memory_extraction: '记忆提取',
    memory_update: '记忆更新',
  }
  const { title: enumTitle, color: statusColor } = useEvaluationEnums()
  const payloadTab = ref('request')
  watch(
    () => props.item.id,
    () => {
      payloadTab.value = 'request'
    }
  )
  const question = computed(() => {
    const input = props.item.item_snapshot?.input_data
    if (typeof input === 'string') return input
    const object = resultObject(input)
    if (typeof object.query === 'string') return object.query
    if (typeof object.question === 'string') return object.question
    return undefined
  })
  const expectedAnswer = computed(() =>
    typeof resultObject(props.item.resolved_expected_output).answer === 'string'
      ? resultObject(props.item.resolved_expected_output).answer
      : undefined
  )
  const actualAnswer = computed(() =>
    typeof props.item.actual_output === 'string'
      ? props.item.actual_output
      : typeof resultObject(props.item.actual_output).answer === 'string'
      ? resultObject(props.item.actual_output).answer
      : undefined
  )
  const memories = computed<unknown[]>(() => {
    const retrieval = resultObject(props.item.actual_output).retrieval ?? props.item.actual_output
    return Array.isArray(retrieval) ? retrieval : resultArray(resultObject(retrieval).top_items)
  })
  const datasetTitle = computed(
    () =>
      `${props.datasetName || `数据集 #${props.dataset?.id ?? '—'}`} · V${
        props.dataset?.version_no ?? '—'
      }`
  )
  const normalize = (text: string) => text.trim().replace(/\s+/g, ' ')
  const memoryEvidence = (memory: unknown) =>
    resultArray(resultObject(memory).evidence).map(resultObject)
  const memoryContent = (memory: unknown) => {
    if (typeof memory === 'string') return memory
    const content = resultObject(memory).content
    return typeof content === 'string' ? content : undefined
  }
  const memoryExcerpts = (memory: unknown): string[] =>
    memoryEvidence(memory)
      .map((source) => source.excerpt)
      .filter((value): value is string => typeof value === 'string' && Boolean(value.trim()))
  const expectedSources = computed(() => {
    const expected = resultObject(props.item.resolved_expected_output)
    const excerpts = [
      ...(Array.isArray(expected.source_excerpts) ? expected.source_excerpts : []),
      expected.source_excerpt,
    ].filter((value): value is string => typeof value === 'string' && Boolean(value.trim()))
    const turns = props.item.details?.turns
    const scoredTurn = (turns ? [...turns].reverse() : []).find((turn) => turn.scored)
    const evidence = (scoredTurn?.context ?? props.item.item_snapshot?.context)?.source_evidence
    const materials = (Array.isArray(evidence) ? evidence : [])
      .map((source: unknown) =>
        typeof source === 'string' ? { excerpt: source } : resultObject(source)
      )
      .filter(
        (source): source is Record<string, unknown> & { excerpt: string } =>
          typeof source.excerpt === 'string' && Boolean(source.excerpt.trim())
      )
    const texts =
      expectedAnswer.value !== undefined || actualAnswer.value !== undefined || !excerpts.length
        ? materials.map((source) => source.excerpt)
        : excerpts
    return [...new Set<string>(texts)].map((text) => ({
      text,
      time: materials.find(
        (source) =>
          typeof source.excerpt === 'string' && normalize(source.excerpt) === normalize(text)
      )?.occurred_at,
      ranks: memories.value.flatMap((memory, index) =>
        memoryExcerpts(memory).some((excerpt) => normalize(excerpt) === normalize(text))
          ? [index + 1]
          : []
      ),
    }))
  })
  const matchesExpected = (memory: unknown) =>
    memoryExcerpts(memory).some((excerpt) =>
      expectedSources.value.some((source) => normalize(source.text) === normalize(excerpt))
    )
</script>
<style scoped>
  .mango-item-result-content {
    container-type: inline-size;
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-item-result-section {
    min-width: 0;
    padding: var(--m-card-padding);
    background: var(--m-surface);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
  }
  .mango-item-result-section > .mango-section-title {
    margin: 0 0 8px;
    font-size: 14px;
  }
  .mango-item-result-text {
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.7;
  }
  .mango-item-result-meta {
    margin: 0;
    color: var(--m-muted);
    overflow-wrap: anywhere;
    line-height: 1.6;
  }
  .mango-item-answer-comparison {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }
  .mango-item-source {
    padding: 12px 0;
    border-top: 1px solid var(--m-border);
  }
  .mango-item-source:first-of-type {
    margin-top: 8px;
  }
  .mango-item-source:last-child {
    padding-bottom: 0;
  }
  .mango-item-source-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .mango-item-memory-list {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .mango-item-memory-evidence {
    margin-top: 8px;
  }
  .mango-item-judge-quotes {
    display: grid;
    gap: 8px;
    margin: 8px 0 0;
  }
  .mango-item-judge-quotes dt {
    color: var(--m-muted);
    margin-bottom: 4px;
  }
  .mango-item-judge-quotes dd {
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.7;
  }
  @container (max-width: 680px) {
    .mango-item-answer-comparison {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
