<template>
  <!--  <div class="h-full-vh">-->
  <router-view v-slot="{ Component, route }">
    <keep-alive :include="cacheRoutes.cachedRoutes">
      <component :is="Component" :key="route.fullPath" />
    </keep-alive>
  </router-view>
  <!--  </div>-->
</template>

<script lang="ts">
  import useAppConfigStore from '@/store/modules/app-config'
  import useCachedRouteStore from '@/store/modules/cached-routes'
  import { defineComponent } from 'vue'

  export default defineComponent({
    name: 'Main',
    setup() {
      const appStore = useAppConfigStore()
      const cacheRoutes = useCachedRouteStore()
      return {
        appStore,
        cacheRoutes,
      }
    },
  })
</script>

<style scoped>
  .h-full-vh {
    height: calc(94vh - 45px);
  }
</style>
