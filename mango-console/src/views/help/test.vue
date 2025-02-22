<template>
  <CodeEditor :code="yourCode" />
</template>

<script setup lang="ts">
  import CodeEditor from '@/components/CodeEditor.vue'

  const yourCode = `print("Hello, World!")`
</script>
