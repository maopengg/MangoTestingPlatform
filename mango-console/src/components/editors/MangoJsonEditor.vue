<template>
  <div class="mango-json-editor" :style="{ minHeight }">
    <CodeEditor
      :model-value="modelValue"
      language="json"
      :readonly="disabled"
      :placeholder="placeholder"
      :code-style="{ height: '100%', minHeight }"
      @update:model-value="$emit('update:modelValue', $event)"
    />
  </div>
</template>

<script lang="ts" setup>
  import CodeEditor from '@/components/editors/CodeEditor.vue'

  withDefaults(
    defineProps<{
      modelValue: string
      placeholder?: string
      minHeight?: string
      disabled?: boolean
    }>(),
    {
      placeholder: '请输入 JSON 内容',
      minHeight: '320px',
      disabled: false,
    }
  )

  defineEmits<{
    (event: 'update:modelValue', value: string): void
  }>()
</script>

<style scoped lang="less">
  .mango-json-editor {
    width: 100%;
    height: 100%;
    min-height: inherit;
  }

  .mango-json-editor :deep(.code-editor),
  .mango-json-editor :deep(.cm-editor) {
    height: 100%;
    min-height: inherit;
  }

  .mango-json-editor :deep(.cm-scroller) {
    min-height: inherit;
  }
</style>
