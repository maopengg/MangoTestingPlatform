<template>
  <a-form-item class="mango-simple-form-item" label="步骤执行时机">
    <a-select :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
      <a-option :value="false">正常流程</a-option>
      <a-option :value="true">最终恢复</a-option>
    </a-select>
  </a-form-item>
  <p class="mango-step-timing-hint">
    正常流程按步骤顺序执行；最终恢复在主流程结束或失败后执行，沿用场景重试配置。
    恢复步骤失败后仍继续后续恢复，但整个用例会判为失败。
  </p>
</template>

<script setup lang="ts">
  defineProps<{ modelValue: boolean }>()
  defineEmits<{ (event: 'update:modelValue', value: boolean): void }>()
</script>

<style scoped>
  .mango-step-timing-hint {
    color: var(--m-muted);
    line-height: 1.6;
    margin: 0;
  }
</style>
