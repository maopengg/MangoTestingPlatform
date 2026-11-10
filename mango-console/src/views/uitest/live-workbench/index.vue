<template>
  <UiLiveWorkbenchPanel
    v-bind="workbenchRoute"
  />
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import { useRoute } from 'vue-router'
  import UiLiveWorkbenchPanel from '@/components/business/UiLiveWorkbenchPanel.vue'
  import { liveWorkbenchRoute } from './config'

  const route = useRoute()
  const workbenchRoute = computed(() => liveWorkbenchRoute(route.query))
</script>
