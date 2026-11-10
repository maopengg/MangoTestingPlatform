<template>
  <section class="mango-grader-editor">
    <div class="mango-section-title"
      ><span>{{ title }}</span
      ><a-button v-if="!disabled" size="small" :loading="loading" @click="add"
        >添加评分项</a-button
      ></div
    >
    <p v-if="modelValue.length" class="mango-grader-rule-hint"
      >参与判定的评分项均须通过；权重仅影响综合分，权重为 0 且非硬门禁的评分项仅记录结果。</p
    >
    <a-table
      v-if="modelValue.length"
      :data="modelValue"
      :columns="columns"
      :pagination="false"
      :bordered="false"
      :scroll="{ x: 800 }"
      size="small"
    >
      <template #grader="{ record, rowIndex }"
        ><div class="mango-grader-editor__select"
          ><a-select
            :model-value="`${record.grader_key}@${record.grader_version}`"
            :options="options"
            :disabled="disabled"
            @change="choose(rowIndex, String($event))" /></div
      ></template>
      <template #threshold="{ record, rowIndex }"
        ><a-input-number
          :model-value="record.threshold"
          :min="0"
          :max="100"
          :disabled="disabled || loading"
          :loading="loading"
          @change="update(rowIndex, { threshold: $event })"
      /></template>
      <template #weight="{ record, rowIndex }"
        ><a-input-number
          :model-value="record.weight"
          :min="0"
          :disabled="disabled"
          @change="update(rowIndex, { weight: $event })"
      /></template>
      <template #hardGate="{ record, rowIndex }"
        ><a-switch
          :model-value="record.hard_gate"
          @change="update(rowIndex, { hard_gate: $event })"
          :disabled="disabled || isModel(record.grader_key)"
      /></template>
      <template #enabled="{ record, rowIndex }"
        ><a-switch
          :model-value="record.enabled"
          :disabled="disabled"
          @change="update(rowIndex, { enabled: $event })"
      /></template>
      <template #actions="{ rowIndex }"
        ><MangoTableActions
          :actions="[
            { label: '参数', onClick: () => (expanded = expanded === rowIndex ? -1 : rowIndex) },
            { label: '移除', danger: true, hidden: disabled, onClick: () => remove(rowIndex) },
          ]"
      /></template>
    </a-table>
    <div
      v-if="expanded >= 0 && modelValue[expanded]"
      class="mango-soft-panel mango-grader-parameter-panel"
    >
      <div class="mango-section-title">{{ selected?.name || modelValue[expanded].grader_key }}</div>
      <p v-if="selected?.description" class="mango-grader-rule-hint">{{ selected.description }}</p>
      <ParameterForm
        :model-value="modelValue[expanded].parameters"
        :schema="selected?.parameters_schema"
        :disabled="disabled"
        @update:model-value="update(expanded, { parameters: $event })"
      />
    </div>
    <div v-if="!modelValue.length" class="mango-empty-state">{{ emptyText }}</div>
  </section>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue'
  import ParameterForm from './ParameterForm.vue'
  import { formatVersion } from './presentation'
  import { defaultGrader } from '../case/config'
  import type { GraderBinding, GraderCatalogEntry } from '../types'
  const props = withDefaults(
    defineProps<{
      modelValue: GraderBinding[]
      catalog: GraderCatalogEntry[]
      title?: string
      disabled?: boolean
      loading?: boolean
      emptyText?: string
    }>(),
    { title: '评分项', disabled: false, emptyText: '尚未配置评分项' }
  )
  const emit = defineEmits<{ (event: 'update:modelValue', value: GraderBinding[]): void }>()
  const expanded = ref(-1)
  const columns = [
    { title: '评分器与版本', slotName: 'grader', ellipsis: true, tooltip: true },
    { title: '通过阈值', slotName: 'threshold', width: 125, align: 'center' },
    { title: '综合分权重', slotName: 'weight', width: 110, align: 'center' },
    { title: '硬门禁', slotName: 'hardGate', width: 90, align: 'center' },
    { title: '启用', slotName: 'enabled', width: 80, align: 'center' },
    { title: '操作', slotName: 'actions', width: 160, fixed: 'right', align: 'center' },
  ]
  const options = computed(() => {
    const current = props.catalog.map((item) => ({
      label: `${item.name} @${formatVersion(item.grader_version)}`,
      value: `${item.grader_key}@${item.grader_version}`,
    }))
    const legacy = props.modelValue
      .filter(
        (item, index, all) =>
          !current.some((option) => option.value === `${item.grader_key}@${item.grader_version}`) &&
          all.findIndex(
            (other) =>
              other.grader_key === item.grader_key && other.grader_version === item.grader_version
          ) === index
      )
      .map((item) => ({
        label: `${
          props.catalog.find((entry) => entry.grader_key === item.grader_key)?.name || '评分器'
        }（旧口径，请重新选择）`,
        value: `${item.grader_key}@${item.grader_version}`,
        disabled: true,
      }))
    return [...current, ...legacy]
  })
  const selected = computed(() => {
    const item = props.modelValue[expanded.value]
    return props.catalog.find(
      (row) => row.grader_key === item?.grader_key && row.grader_version === item?.grader_version
    )
  })
  function isModel(key: string) {
    return props.catalog.some((item) => item.grader_key === key && item.category === 'model')
  }
  function add() {
    if (props.disabled || props.loading) return
    emit('update:modelValue', [
      ...props.modelValue,
      { ...defaultGrader(), metric_key: `metric_${crypto.randomUUID().replace(/-/g, '')}` },
    ])
    expanded.value = props.modelValue.length
  }
  function remove(index: number) {
    if (props.disabled) return
    emit(
      'update:modelValue',
      props.modelValue.filter((_, i) => i !== index)
    )
    expanded.value = -1
  }
  function choose(index: number, value: string) {
    if (props.disabled || props.loading) return
    const [key, version] = value.split('@')
    const next = props.modelValue.map((row, i) =>
      i === index
        ? {
            ...row,
            grader_key: key,
            grader_version: Number(version),
            parameters: {},
            hard_gate: isModel(key) ? false : row.hard_gate,
          }
        : row
    )
    emit('update:modelValue', next)
  }
  function update(index: number, patch: Partial<GraderBinding>) {
    if (props.disabled || !props.modelValue[index]) return
    emit(
      'update:modelValue',
      props.modelValue.map((row, i) => (i === index ? { ...row, ...patch } : row))
    )
  }
</script>
<style scoped>
  .mango-grader-rule-hint {
    color: var(--m-muted);
    margin: var(--m-page-gap) 0;
    line-height: 1.6;
    font-size: var(--m-font-caption);
  }
  .mango-grader-editor__select {
    width: 100%;
    max-width: 360px;
  }
  .mango-grader-editor {
    min-width: 0;
    max-width: 1120px;
  }
  .mango-grader-parameter-panel {
    margin-top: var(--m-page-gap);
    padding: var(--m-card-padding);
  }
</style>
