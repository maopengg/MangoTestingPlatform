<template>
  <section class="mango-quality-gate-editor">
    <div class="mango-section-title">
      <strong>质量门禁</strong>
      <a-button v-if="!disabled" size="small" @click="add">添加门禁</a-button>
    </div>
    <a-table v-if="modelValue.length" :data="modelValue" :pagination="false" :columns="columns" :scroll="{ x: 840 }" size="small">
      <template #metric="{ record }">
        <a-select :model-value="record.metric_key ? `metric:${record.metric_key}` : record.key" :options="options(record)" :disabled="disabled" placeholder="选择统计指标" allow-clear @change="choose(record, $event)" />
        <span v-if="record.group_by" class="mango-quality-gate-hint">统计范围：{{ record.group_by }}</span>
      </template>
      <template #operator="{ record }"><a-select v-model="record.operator" :options="gateOperators" :disabled="disabled" @change="record.operator === 'zero' && (record.threshold = 0)" /></template>
      <template #threshold="{ record }"><a-input-number v-model="record.threshold" :disabled="disabled || record.operator === 'zero'" /></template>
      <template #severity="{ record }"><a-select v-model="record.severity" :options="gateSeverities" :disabled="disabled" /></template>
      <template #actions="{ rowIndex }"><MangoTableActions :actions="[{ label: '移除', danger: true, hidden: disabled, onClick: () => remove(rowIndex) }]" /></template>
    </a-table>
    <p v-else class="mango-quality-gate-hint">未设置额外门禁，按通过条件判断本次执行。</p>
    <p v-if="modelValue.some(item => ['valid_rate', 'effect_pass_rate', 'pass_rate'].includes(item.key))" class="mango-quality-gate-hint">比例阈值填写 0～1，例如 0.8 表示 80%。</p>
    <p v-if="error" role="alert" class="mango-quality-gate-error">{{ error }}</p>
  </section>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import { gateMetrics, gateOperators, gateSeverities, qualityGateError } from '../case/config'
  const props = withDefaults(defineProps<{ modelValue: Record<string, any>[]; graders?: Record<string, any>[]; catalog?: Record<string, any>[]; disabled?: boolean }>(), { graders: () => [], catalog: () => [], disabled: false })
  const emit = defineEmits<{ (event: 'update:modelValue', value: Record<string, any>[]): void }>()
  const columns = [
    { title: '统计指标', slotName: 'metric', width: 260 },
    { title: '比较方式', slotName: 'operator', width: 140 },
    { title: '阈值', slotName: 'threshold', width: 140 },
    { title: '未达标时', slotName: 'severity', width: 140 },
    { title: '操作', slotName: 'actions', width: 160, align: 'center', fixed: 'right' },
  ]
  const error = computed(() => qualityGateError(props.modelValue))
  function options(record: Record<string, any>) {
    const items = [...gateMetrics, ...props.graders.filter(item => !record.group_by && item.enabled && item.metric_key).map((item, index) => ({ label: `${props.catalog.find(grader => grader.grader_key === item.grader_key && grader.grader_version === item.grader_version)?.name || `评分项 ${index + 1}`} · 平均分`, value: `metric:${item.metric_key}` }))]
    const value = record.metric_key ? `metric:${record.metric_key}` : record.key
    if (value && !items.some(item => item.value === value)) items.push({ label: value, value })
    return items
  }
  function choose(record: Record<string, any>, value?: string) {
    if (props.disabled) return
    if (value?.startsWith('metric:')) { record.metric_key = value.slice(7); record.key = record.metric_key }
    else { record.key = value || ''; delete record.metric_key }
  }
  function add() { if (!props.disabled) emit('update:modelValue', [...props.modelValue, { key: '', operator: 'gte', threshold: 0, severity: 'critical' }]) }
  function remove(index: number) { if (!props.disabled) emit('update:modelValue', props.modelValue.filter((_, i) => i !== index)) }
</script>
<style scoped>
  .mango-quality-gate-editor { min-width: 0; }
  .mango-quality-gate-hint { color: var(--m-muted); margin: var(--m-page-gap) 0; }
  .mango-quality-gate-error { color: var(--m-danger); margin: var(--m-page-gap) 0; }
</style>
