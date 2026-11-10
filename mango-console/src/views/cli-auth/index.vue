<template>
  <main class="mango-cli-auth-page">
    <a-card class="mango-cli-auth-card" :bordered="false" :aria-busy="status === 'loading'">
      <div class="mango-cli-auth-logo">M</div>
      <h1>芒果 CLI 授权</h1>
      <p role="status" aria-live="polite">{{ statusText }}</p>
      <a-spin v-if="status === 'loading'" :size="scaleDensityPixels(28)" />
      <a-alert v-else-if="status === 'error'" type="error">{{ errorMessage }}</a-alert>
      <a-button v-if="status === 'error'" type="primary" size="small" @click="authorize">
        重新授权
      </a-button>
    </a-card>
  </main>
</template>

<script setup lang="ts">
  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { authorizeCli } from '@/api/cli-auth'
  import useUserStore from '@/store/modules/user'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { authorizationMessages, authorizationStatusText } from './config'
  import {
    authorizationErrorMessage,
    authorizationParams,
    isAuthorizationResult,
    validatedCallback,
  } from './params'

  type AuthorizationStatus = keyof typeof authorizationStatusText
  const route = useRoute(),
    router = useRouter(),
    userStore = useUserStore()
  const status = ref<AuthorizationStatus>('loading'),
    errorMessage = ref('')
  const statusText = computed(() => authorizationStatusText[status.value])
  let active = true,
    mounted = false,
    requestSequence = 0,
    pendingRequest: number | null = null

  function invalidate() {
    ++requestSequence
    pendingRequest = null
  }
  async function authorize() {
    if (
      !active ||
      route.path !== '/cli-auth' ||
      pendingRequest !== null ||
      status.value === 'success'
    )
      return
    const request = ++requestSequence,
      fullPath = route.fullPath,
      token = userStore.token
    const current = () =>
      active &&
      request === requestSequence &&
      route.path === '/cli-auth' &&
      route.fullPath === fullPath &&
      userStore.token === token
    pendingRequest = request
    status.value = 'loading'
    errorMessage.value = ''
    try {
      if (!token) {
        const failure = await router.replace({ path: '/login', query: { redirect: fullPath } })
        if (failure && current()) throw new Error(authorizationMessages.loginRedirectFailed)
        return
      }
      const payload = authorizationParams(route.query)
      if (!payload) throw new Error(authorizationMessages.invalidParams)
      const callback = validatedCallback(payload.redirect_uri)
      if (!callback) throw new Error(authorizationMessages.invalidParams)
      const response = await authorizeCli(payload)
      if (!current()) return
      const result: unknown = response.data
      if (!isAuthorizationResult(result)) throw new Error(authorizationMessages.invalidResult)
      callback.searchParams.set('code', result.code)
      callback.searchParams.set('state', payload.state)
      status.value = 'success'
      window.location.assign(callback.toString())
    } catch (error: unknown) {
      if (!current()) return
      status.value = 'error'
      errorMessage.value = authorizationErrorMessage(error)
    } finally {
      if (pendingRequest === request) pendingRequest = null
    }
  }

  watch([() => route.fullPath, () => userStore.token], () => {
    invalidate()
    if (route.path !== '/cli-auth') return
    status.value = 'loading'
    errorMessage.value = ''
    if (active && mounted) void authorize()
  })
  function deactivate() {
    active = false
    invalidate()
  }
  onMounted(() => {
    mounted = true
    void authorize()
  })
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)
  onActivated(() => {
    if (!active) {
      active = true
      if (mounted && status.value !== 'success') void authorize()
    }
  })
</script>

<style scoped lang="less">
  .mango-cli-auth-page {
    box-sizing: border-box;
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
