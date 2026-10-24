<template>
  <div class="mango-evaluation-report-list">
    <section v-for="record in cases" :key="record.id" class="mango-section-card">
      <div class="mango-section-title">{{ record.case_name }} · {{ payload(record).execution_no }}</div>
      <a-descriptions :column="2" size="small">
        <a-descriptions-item label="数据版本">数据集 #{{ payload(record).dataset?.id }} · V{{ payload(record).dataset?.version_no }}</a-descriptions-item>
        <a-descriptions-item label="被测对象">{{ targetText(payload(record).target) }}</a-descriptions-item>
        <a-descriptions-item label="执行结论"><a-tag size="small" :color="enumStore.colors?.[record.status] || 'gray'">{{ statusText(record.status) }}</a-tag></a-descriptions-item>
        <a-descriptions-item label="有效 / 总测次">{{ payload(record).summary?.valid ?? '—' }} / {{ record.case_sum }}</a-descriptions-item>
        <a-descriptions-item label="平均分">{{ payload(record).summary?.average_score ?? '—' }}</a-descriptions-item>
        <a-descriptions-item label="有效率">{{ percent(payload(record).summary?.valid_rate) }}</a-descriptions-item>
        <a-descriptions-item label="有效题通过率">{{ percent(payload(record).summary?.effect_pass_rate) }}</a-descriptions-item>
        <a-descriptions-item label="无效条目">{{ payload(record).summary?.invalid ?? '—' }}</a-descriptions-item>
      </a-descriptions>
      <a-alert v-if="payload(record).error_message" type="error">{{ payload(record).error_message }}</a-alert>
      <a-descriptions v-if="payload(record).summary?.memory_qa" :column="3" size="small" title="记忆问答能力">
        <a-descriptions-item label="正确率">{{ percent(payload(record).summary.memory_qa.rates.correct) }}</a-descriptions-item>
        <a-descriptions-item label="幻觉率">{{ percent(payload(record).summary.memory_qa.rates.hallucination) }}</a-descriptions-item>
        <a-descriptions-item label="遗漏率">{{ percent(payload(record).summary.memory_qa.rates.omission) }}</a-descriptions-item>
      </a-descriptions>
      <a-table :columns="evaluationMetricColumns" :data="metrics(record)" :pagination="false" :bordered="false" :scroll="{ x: 600 }" row-key="key" size="small" />
      <section v-if="payload(record).summary?.ai_summary" class="mango-soft-panel">
        <div class="mango-section-title">AI 总结</div>
        <template v-if="payload(record).summary.ai_summary.status === 'completed'">
          <p>{{ payload(record).summary.ai_summary.overview }}</p>
          <p v-for="finding in payload(record).summary.ai_summary.findings" :key="finding">{{ finding }}</p>
          <p v-for="tip in payload(record).summary.ai_summary.recommendations" :key="tip">{{ tip }}</p>
        </template>
        <a-alert v-else type="warning">总结生成失败，不影响评分结果。{{ payload(record).summary.ai_summary.error_message }}</a-alert>
      </section>
      <div class="mango-evaluation-report-note">统计来自本次执行冻结的数据和评分配置；无效条目不计入能力指标。未配置的能力不作统计。</div>
    </section>
  </div>
</template>

<script setup lang="ts">
  import { evaluationMetricColumns } from './config'
  const props = defineProps<{ cases: any[]; enumStore: any }>()
  function payload(record: any) { return record.children || {} }
  function percent(value: any) { return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—' }
  function statusText(value: number) { return props.enumStore.task_status?.find((item: any) => Number(item.key) === value)?.title || '未评测' }
  function targetText(target: any) {
    if (target?.type === 'script') return 'Python 脚本'
    return `接口 #${target?.ref_id ?? '—'} · ${target?.version_ref?.kind === 'api_info_release' ? '发布' : '修订'} #${target?.version_ref?.id ?? '—'}`
  }
  function metrics(record: any) {
    return Object.entries(payload(record).summary?.metrics || {}).flatMap(([key, metric]: [string, any]) =>
      (metric.variants || [metric]).map((entry: any, index: number) => ({
        ...entry, key: `${key}-${index}`, version: `V${entry.grader_version}`,
        grader_key: payload(record).grader_names?.[entry.grader_key] || entry.grader_key,
        counts: `${entry.passed} / ${entry.total}`, pass_rate_text: percent(entry.pass_rate),
        average_score: entry.average_score ?? '—',
      }))
    )
  }
</script>

<style scoped>
  .mango-evaluation-report-list { display: grid; gap: var(--m-page-gap); min-width: 0; }
  .mango-section-card { padding: var(--m-card-padding); min-width: 0; }
  .mango-evaluation-report-note { color: var(--m-muted); margin-top: var(--m-page-gap); font-size: 12px; }
</style>
