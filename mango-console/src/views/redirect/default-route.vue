<template>
  <div class="mango-default-route" role="status" :aria-busy="loading">
    <a-spin v-if="loading" dot tip="正在加载页面" />
    <div v-else-if="failed" class="mango-empty-state">
      <span>页面跳转失败，请重试。</span>
      <a-button size="small" :loading="loading" @click="redirect">重新加载</a-button>
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
      const router = useRouter()
      const route = useRoute()
      const user = useUserStore()
      const loading = ref(true),
        failed = ref(false)
      let entry = route.fullPath
      let version = 0,
        active = true,
        disposed = false,
        resumePending = false
      let pending: Promise<void> | null = null
      const available = () =>
        !disposed &&
        active &&
        route.fullPath === entry &&
        route.name === 'defaultRouteName' &&
        (typeof document === 'undefined' || !document.hidden)

      function redirect(): Promise<void> {
        if (!available()) return Promise.resolve()
        if (pending) return pending
        const request = version
        const target = {
          path: route.path,
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
            if (request !== version || !available()) return
            if (router.hasRoute('defaultRouteName')) router.removeRoute('defaultRouteName')
            // 只传地址信息，让新注册的路由重新匹配，不能带回旧 matched/meta。
            const failure = await router.replace(target)
            if (isNavigationFailure(failure) && request === version && available())
              failed.value = true
          } catch {
            if (request === version && available()) failed.value = true
          } finally {
            pending = null
            if (request === version && available()) loading.value = false
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
        () => [user.userId, user.roleId, user.token, user.selected_environment],
        () => {
          pause()
          resume()
        },
        { flush: 'sync' }
      )
      watch(
        () => route.fullPath,
        () => {
          pause()
          if (route.name === 'defaultRouteName') entry = route.fullPath
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
  .mango-default-route {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    min-height: 0;
    padding: var(--m-page-gap);
    color: var(--m-text);
    background: var(--m-bg);
  }
</style>
