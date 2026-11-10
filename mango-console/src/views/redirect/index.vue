<template>
  <div class="mango-route-refresh" role="status" :aria-busy="loading">
    <a-spin v-if="loading" dot tip="正在刷新页面" />
    <div v-else-if="failed" class="mango-empty-state">
      <span>页面刷新失败，请重试。</span>
      <a-button size="small" :loading="loading" @click="redirect">重试</a-button>
    </div>
  </div>
</template>

<script lang="ts">
  import {
    defineComponent,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    ref,
    watch,
  } from 'vue'
  import { isNavigationFailure, useRoute, useRouter } from 'vue-router'
  import useUserStore from '@/store/modules/user'

  export default defineComponent({
    setup() {
      const route = useRoute(),
        router = useRouter(),
        user = useUserStore()
      const ownRecord = route.matched[route.matched.length - 1]
      const loading = ref(true),
        failed = ref(false)
      let version = 0,
        active = true,
        disposed = false,
        resumePending = false
      let pending: Promise<void> | null = null
      const available = () =>
        !disposed &&
        active &&
        route.matched.includes(ownRecord) &&
        (route.path === '/redirect' || route.path.startsWith('/redirect/')) &&
        (typeof document === 'undefined' || !document.hidden)
      function redirect(): Promise<void> {
        if (!available()) return Promise.resolve()
        if (pending) return pending
        const request = version
        // route.path 保留编码；params 已解码，重新拼接会改变含 %2F、%3F 等字符的路径。
        const target = {
          path: route.path.slice('/redirect'.length) || '/',
          query: Object.fromEntries(
            Object.entries(route.query).map(([key, value]) => [
              key,
              Array.isArray(value) ? [...value] : value,
            ])
          ),
          hash: route.hash,
        }
        loading.value = true
        failed.value = false
        const task = Promise.resolve().then(async () => {
          try {
            if (!available() || request !== version) return
            const failure = await router.replace(target)
            if (isNavigationFailure(failure) && available() && request === version)
              failed.value = true
          } catch {
            if (available() && request === version) failed.value = true
          } finally {
            pending = null
            if (available() && request === version) loading.value = false
            if (resumePending) {
              resumePending = false
              void redirect()
            }
          }
        })
        pending = task
        return task
      }
      function pause(): void {
        version++
        resumePending = false
      }
      function resume(): void {
        if (!available()) return
        if (pending) resumePending = true
        else void redirect()
      }
      watch(
        () => [route.fullPath, user.userId, user.roleId, user.token, user.selected_environment],
        () => {
          pause()
          resume()
        },
        { flush: 'sync' }
      )
      function visibilityChanged(): void {
        if (typeof document !== 'undefined' && document.hidden) pause()
        else resume()
      }
      onMounted(() => {
        if (typeof document !== 'undefined')
          document.addEventListener('visibilitychange', visibilityChanged)
        void redirect()
      })
      onActivated(() => {
        if (!active) {
          active = true
          resume()
        }
      })
      onDeactivated(() => {
        active = false
        pause()
      })
      onBeforeUnmount(() => {
        disposed = true
        pause()
        if (typeof document !== 'undefined')
          document.removeEventListener('visibilitychange', visibilityChanged)
      })
      return { loading, failed, redirect }
    },
  })
</script>

<style scoped>
  .mango-route-refresh {
    display: flex;
    height: 100%;
    min-height: 0;
    align-items: center;
    justify-content: center;
    padding: var(--m-page-gap);
    background: var(--m-bg);
    color: var(--m-text);
  }
</style>
