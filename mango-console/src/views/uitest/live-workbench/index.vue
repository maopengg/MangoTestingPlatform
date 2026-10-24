<template>
  <UiLiveWorkbenchPanel
    :mode="mode"
    :page-id="pageId"
    :page-step-id="pageStepId"
    :test-env="testEnv"
    :category="category"
  />
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import { useRoute } from 'vue-router'
  import UiLiveWorkbenchPanel from '@/components/business/UiLiveWorkbenchPanel.vue'

  const route = useRoute()
  const mode = computed<'element' | 'step'>(() =>
    route.query.mode === 'step' ? 'step' : 'element'
  )
  const pageId = computed(() => route.query.pageId as string | undefined)
  const pageStepId = computed(() => route.query.pageStepId as string | undefined)
  const testEnv = computed(() => route.query.testEnv as string | undefined)
  const category = computed(() => route.query.category as string | undefined)
</script>
