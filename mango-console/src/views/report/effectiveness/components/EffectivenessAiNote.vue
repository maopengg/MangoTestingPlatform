<template>
  <p v-if="content" class="mango-effectiveness-ai-note">{{ content }}</p>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  const props = withDefaults(
    defineProps<{
      text?: string
    }>(),
    {
      text: '',
    }
  )

  const content = computed(() => String(props.text || '').trim())
</script>

<style scoped>
  .mango-effectiveness-ai-note {
    display: block;
    overflow: visible;
    width: 100%;
    margin: auto 0 2px;
    padding: 6px 2px 0;
    box-sizing: border-box;
    border-top: 1px solid var(--m-border);
    color: var(--m-text-2);
    font-size: 11px;
    line-height: 17px;
    overflow-wrap: anywhere;
    white-space: pre-line;
    word-break: break-word;
  }
</style>
