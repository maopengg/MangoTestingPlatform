<template>
  <router-view />
</template>

<script setup lang="ts">
  import { onMounted, watchEffect } from 'vue'
  import { useRoute } from 'vue-router'
  import usePlatformBrandingStore from '@/store/modules/platform-branding'

  const branding = usePlatformBrandingStore()
  const route = useRoute()
  watchEffect(() => {
    const pageTitle = typeof route.meta.title === 'string' ? route.meta.title : ''
    document.title = pageTitle ? `${branding.projectName} | ${pageTitle}` : branding.projectName
  })
  onMounted(() => { void branding.loadPublicConfig().catch(() => {}) })
</script>
