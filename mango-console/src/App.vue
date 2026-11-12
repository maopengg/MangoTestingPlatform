<template>
  <router-view />
</template>

<script setup lang="ts">
  import { onBeforeUnmount, onMounted, watchEffect } from 'vue'
  import { useRoute } from 'vue-router'
  import usePlatformBrandingStore from '@/store/modules/platform-branding'
  import useUserPreferencesStore from '@/store/modules/user-preferences'

  const stopPreferences = useUserPreferencesStore().start()
  onBeforeUnmount(stopPreferences)
  const branding = usePlatformBrandingStore()
  const route = useRoute()
  watchEffect(() => {
    const pageTitle = typeof route.meta.title === 'string' ? route.meta.title : ''
    document.title = pageTitle ? `${branding.projectName} | ${pageTitle}` : branding.projectName
  })
  onMounted(() => { void branding.loadPublicConfig().catch(() => {}) })
</script>
