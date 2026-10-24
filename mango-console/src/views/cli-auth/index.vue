<template>
  <main class="mango-cli-auth-page">
    <a-card class="mango-cli-auth-card" :bordered="false">
      <div class="mango-cli-auth-logo">M</div>
      <h1>芒果 CLI 授权</h1>
      <p>{{ statusText }}</p>
      <a-spin v-if="status === 'loading'" :size="28" />
      <a-alert v-else-if="status === 'error'" type="error">{{ errorMessage }}</a-alert>
      <a-button v-if="status === 'error'" type="primary" size="small" @click="authorize">
        重新授权
      </a-button>
    </a-card>
  </main>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { post } from '@/api/http'
  import useUserStore from '@/store/modules/user'

  type Status = 'loading' | 'error' | 'success'
  interface AuthorizationResult {
    code: string
    expires_in: number
  }

  const route = useRoute()
  const router = useRouter()
  const userStore = useUserStore()
  const status = ref<Status>('loading')
  const errorMessage = ref('')
  const statusText = computed(() => {
    if (status.value === 'success') return '授权已完成，正在返回终端…'
    if (status.value === 'error') return '未能完成授权'
    return '正在安全地授权当前 CLI…'
  })

  function queryValue(name: string): string {
    const value = route.query[name]
    return typeof value === 'string' ? value : ''
  }

  function validatedCallback(value: string): URL | null {
    try {
      const url = new URL(value)
      if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || url.pathname !== '/callback') {
        return null
      }
      if (!url.port || url.username || url.password || url.search || url.hash) return null
      return url
    } catch {
      return null
    }
  }

  async function authorize() {
    status.value = 'loading'
    errorMessage.value = ''
    if (!userStore.token) {
      await router.replace({ path: '/login', query: { redirect: route.fullPath } })
      return
    }
    const redirectUri = queryValue('redirect_uri')
    const state = queryValue('state')
    const codeChallenge = queryValue('code_challenge')
    const version = queryValue('version')
    const callback = validatedCallback(redirectUri)
    if (!callback || !state || !codeChallenge || !version) {
      status.value = 'error'
      errorMessage.value = 'CLI 授权参数无效，请返回终端重新执行登录命令。'
      return
    }
    try {
      const response = await post<AuthorizationResult>({
        url: '/cli/auth/authorize',
        data: { redirect_uri: redirectUri, state, code_challenge: codeChallenge, version },
        silentError: true,
      })
      const data = response.data as AuthorizationResult
      status.value = 'success'
      callback.searchParams.set('code', data.code)
      callback.searchParams.set('state', state)
      window.location.assign(callback.toString())
    } catch (error: any) {
      status.value = 'error'
      errorMessage.value = error?.message || '授权失败，请重试。'
    }
  }

  onMounted(authorize)
</script>

<style scoped lang="less">
  .mango-cli-auth-page {
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: 24px;
    background: var(--m-bg);
  }

  .mango-cli-auth-card {
    width: min(420px, 100%);
    text-align: center;
    box-shadow: var(--m-shadow);

    :deep(.arco-card-body) {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      padding: 40px;
    }

    h1,
    p {
      margin: 0;
    }

    p {
      color: var(--m-text-2);
    }
  }

  .mango-cli-auth-logo {
    width: 48px;
    height: 48px;
    display: grid;
    place-items: center;
    border-radius: 12px;
    color: var(--m-surface);
    background: var(--m-primary);
    font-size: 24px;
    font-weight: 700;
  }
</style>
