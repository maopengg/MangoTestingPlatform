<template>
  <section
    class="mango-step-condition"
    :class="{ 'mango-step-condition--error': Boolean(errorMessage) }"
  >
    <div class="mango-step-condition__head">
      <strong><span v-if="required" class="mango-step-condition__required">*</span>{{ title }}</strong>
      <div class="mango-step-condition__tools">
        <a-select :model-value="normalizedModelValue.operator" :disabled="disabled" size="mini" @update:model-value="updateOperator">
          <a-option value="all">全部满足</a-option>
          <a-option value="any">任一满足</a-option>
        </a-select>
        <a-button size="mini" :disabled="disabled" @click="add">添加条件</a-button>
      </div>
    </div>
    <div v-for="(item, index) in normalizedModelValue.conditions" :key="index" class="mango-step-condition__row">
      <a-select :model-value="item.type" :disabled="disabled" @update:model-value="updateType(index, String($event))">
        <a-option value="visible_text">可见文本</a-option><a-option value="url_path">URL路径</a-option>
        <a-option value="page_title">页面标题</a-option><a-option value="element_state">元素状态</a-option>
      </a-select>
      <a-select :model-value="item.matcher" :disabled="disabled" @update:model-value="field(index, 'matcher', $event)">
        <a-option v-for="option in matcherOptions(item.type)" :key="option.value" :value="option.value">
          {{ option.label }}
        </a-option>
      </a-select>
      <a-select
        v-if="item.type === 'element_state'"
        :model-value="item.element_id"
        :disabled="disabled"
        allow-search
        allow-clear
        placeholder="请选择页面元素"
        @update:model-value="field(index, 'element_id', $event)"
      >
        <a-option
          v-for="element in selectableElementOptions"
          :key="element.value"
          :value="element.value"
          :label="element.label"
        >
          {{ element.label }}
        </a-option>
      </a-select>
      <div v-else-if="item.type === 'visible_text' && item.matcher === 'count_gte'" class="mango-step-condition__variable">
        <a-input
          :model-value="String(item.expected ?? '')"
          :disabled="disabled"
          placeholder="目标文本"
          @update:model-value="field(index, 'expected', $event)"
        />
        <a-input-number
          :model-value="item.count"
          :disabled="disabled"
          :min="0"
          placeholder="最少次数"
          @update:model-value="field(index, 'count', $event)"
        />
      </div>
      <a-input
        v-else
        :model-value="String(item.expected ?? '')"
        :disabled="disabled"
        placeholder="预期值"
        @update:model-value="field(index, 'expected', $event)"
      />
      <a-button size="mini" status="danger" :disabled="disabled" @click="remove(index)">删除</a-button>
    </div>
    <div v-if="!normalizedModelValue.conditions.length" class="mango-empty-state">暂未配置条件</div>
    <div data-feedback-kind="validation" v-if="errorMessage" class="mango-step-condition__error">{{ errorMessage }}</div>
  </section>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import type { UiStepCondition, UiStepConditionGroup } from '@/types/ui-test/case'
  import { liveId } from './ui-live-workbench'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import type { StepElement } from './ui-page-step'
  const props = withDefaults(
    defineProps<{
      modelValue?: UiStepConditionGroup
      title: string
      disabled?: boolean
      required?: boolean
      errorMessage?: string
      elementOptions?: StepElement[]
    }>(),
    {
      modelValue: () => ({ operator: 'all', conditions: [] }),
      disabled: false,
      required: false,
      errorMessage: '',
      elementOptions: () => [],
    }
  )
  const emit = defineEmits<{ (event: 'update:modelValue', value: UiStepConditionGroup): void }>()
  const normalizedModelValue = computed<UiStepConditionGroup>(() => ({
    operator: props.modelValue?.operator === 'any' ? 'any' : 'all',
    conditions: Array.isArray(props.modelValue?.conditions) ? props.modelValue.conditions : [],
  }))
  const selectableElementOptions = computed(() =>
    props.elementOptions
      .filter(element => liveId(element.id) !== null)
      .map(element => ({
        value: element.id!,
        label: `${element.category || '未分类'} / ${element.name || `元素 #${element.id}`}`,
      }))
  )
  function update(conditions: UiStepCondition[]) { emit('update:modelValue', { ...normalizedModelValue.value, conditions: cloneLosslessJson(conditions) }) }
  function updateOperator(value: string | number | boolean) { emit('update:modelValue', { ...normalizedModelValue.value, operator: value === 'any' ? 'any' : 'all' }) }
  function add() { update([...normalizedModelValue.value.conditions, { type: 'visible_text', matcher: 'contains', expected: '' }]) }
  function remove(index: number) { update(normalizedModelValue.value.conditions.filter((_, row) => row !== index)) }
  function field(index: number, key: 'matcher' | 'element_id' | 'count' | 'expected', value: unknown) {
    const items = cloneLosslessJson(normalizedModelValue.value.conditions), item = items[index]
    if (!item || props.disabled) return
    if (key === 'expected') item.expected = cloneLosslessJson(value)
    if (key === 'element_id') item.element_id = liveId(value) ?? undefined
    if (key === 'count') item.count = typeof value === 'number' && Number.isFinite(value) ? value : undefined
    if (key === 'matcher') { const option = matcherOptions(item.type).find(option => option.value === value); if (!option) return; item.matcher = option.value }
    update(items)
  }
  const matcherMap: Record<string, Array<{ value: UiStepCondition['matcher']; label: string }>> = {
    url_path: [{ value: 'contains', label: '包含' }, { value: 'equals', label: '等于' }, { value: 'starts_with', label: '开头是' }, { value: 'regex', label: '正则' }],
    page_title: [{ value: 'contains', label: '包含' }, { value: 'equals', label: '等于' }, { value: 'starts_with', label: '开头是' }, { value: 'regex', label: '正则' }],
    visible_text: [{ value: 'contains', label: '包含' }, { value: 'equals', label: '等于' }, { value: 'starts_with', label: '开头是' }, { value: 'regex', label: '正则' }, { value: 'count_gte', label: '出现次数不少于' }],
    element_state: [{ value: 'visible', label: '可见' }, { value: 'hidden', label: '隐藏' }, { value: 'enabled', label: '可操作' }, { value: 'editable', label: '可编辑' }, { value: 'checked', label: '已选中' }],
  }
  function matcherOptions(type: string) { return matcherMap[type] || matcherMap.visible_text }
  function updateType(index: number, type: UiStepCondition['type']) {
    const matcher = matcherOptions(type)[0].value
    update(normalizedModelValue.value.conditions.map((item, row) => row === index
      ? { type, matcher, expected: '', element_id: undefined, count: undefined }
      : item))
  }
</script>

<style scoped>
  .mango-step-condition {
    margin-bottom: 14px;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }
  .mango-step-condition--error { border-color: var(--m-danger); }
  .mango-step-condition__head, .mango-step-condition__tools { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .mango-step-condition__row { display: grid; grid-template-columns: 140px 120px 1fr auto; gap: 8px; margin-top: 8px; }
  .mango-step-condition__variable { display: grid; grid-template-columns: minmax(120px, 1fr) minmax(120px, 1fr); gap: 8px; }
  .mango-step-condition__required { margin-right: 4px; color: var(--m-danger); }
  .mango-step-condition__error { margin-top: 8px; color: var(--m-danger); font-size: 12px; }
</style>
