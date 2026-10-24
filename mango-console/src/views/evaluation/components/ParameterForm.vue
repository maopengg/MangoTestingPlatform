<template>
  <div class="mango-grader-parameters" role="group" aria-label="评分器参数">
    <a-form-item v-for="(field, key) in schema?.properties || {}" :key="key" :label="labels[String(key)] || String(key)">
      <a-switch v-if="field.type === 'boolean'" size="small" :model-value="Boolean(modelValue[key])" :disabled="disabled" @change="set(String(key), $event)" />
      <a-input-number v-else-if="field.type === 'number' || field.type === 'integer'" :model-value="modelValue[key]" :min="field.minimum" :max="field.maximum" :precision="field.type === 'integer' ? 0 : undefined" :disabled="disabled" allow-clear @change="set(String(key), $event)" />
      <DataFieldsEditor v-else-if="field.type === 'object' || field.type === 'array'" :model-value="modelValue[key]" :schema="field" :disabled="disabled" @update:model-value="set(String(key), $event)" />
      <a-input v-else :model-value="modelValue[key]" :disabled="disabled" :placeholder="field.description || '留空使用整个对象'" allow-clear @update:model-value="set(String(key), $event)" />
    </a-form-item>
  </div>
</template>
<script setup lang="ts">
  import DataFieldsEditor from './DataFieldsEditor.vue'
  const props = withDefaults(defineProps<{ modelValue: Record<string, any>; schema?: Record<string, any>; disabled?: boolean }>(), { disabled: false })
  const emit = defineEmits<{ (event: 'update:modelValue', value: Record<string, any>): void }>()
  const labels: Record<string, string> = { expected_path: '期望字段路径', actual_path: '输出字段路径', normalize: '文本规范化', absolute_tolerance: '绝对容差', relative_tolerance: '相对容差', schema: '输出 Schema', rubric: '评分标准', max_tokens: '最大输出 Token', confidence_threshold: '置信度阈值', k: '检索 K 值' }
  function set(key: string, value: unknown) {
    const next = { ...props.modelValue }
    if (value == null || value === '') delete next[key]
    else next[key] = value
    emit('update:modelValue', next)
  }
</script>
<style scoped>
  .mango-grader-parameters { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr)); gap: var(--m-page-gap); min-width: 0; }
  .mango-grader-parameters :deep(.arco-form-item) { min-width: 0; margin-bottom: 0; flex-direction: row; }
  .mango-grader-parameters :deep(.arco-form-item-label-col) { flex: 0 0 120px; max-width: 120px; padding-right: var(--m-space-sm); }
  .mango-grader-parameters :deep(.arco-form-item-wrapper-col) { flex: 1; min-width: 0; max-width: none; }
  .mango-grader-parameters :deep(.arco-input-number) { width: 100%; }
</style>
