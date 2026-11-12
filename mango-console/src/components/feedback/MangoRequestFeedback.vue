<template>
  <slot />
  <slot name="action" />
</template>

<script lang="ts">
  export default { name: 'MangoRequestFeedback', inheritAttrs: false }
</script>

<script setup lang="ts">
  import { onActivated, onBeforeUnmount, onDeactivated, onMounted, watch } from 'vue'
  import { reportLoadError } from '@/utils/load-error'

  const props = defineProps<{ message?: string | boolean | null }>()
  let active = true
  let announced = ''
  function notify() {
    const message = typeof props.message === 'string' ? props.message.trim() : ''
    if (!message) { announced = ''; return }
    if (!active || document.visibilityState === 'hidden' || announced === message) return
    announced = message
    reportLoadError(undefined, message)
  }
  watch(() => props.message, notify, { immediate: true, flush: 'post' })
  onMounted(() => document.addEventListener('visibilitychange', notify))
  onActivated(() => { active = true; notify() })
  onDeactivated(() => { active = false })
  onBeforeUnmount(() => document.removeEventListener('visibilitychange', notify))
</script>
