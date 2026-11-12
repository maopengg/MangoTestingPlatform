<template>
  <section class="mango-section-card mango-personal-config" :aria-busy="loading">
    <div class="mango-personal-config__header">
      <h2 class="mango-section-heading">个人配置</h2>
    </div>

    <a-table
      :columns="userConfigColumns"
      :data="items"
      :loading="loading"
      :pagination="false"
      :scroll="{ x: userConfigScrollX }"
      row-key="key"
    >
      <template #value_type="{ record }">
        <a-tag size="small">{{ userConfigValueTypes[record.value_type] }}</a-tag>
      </template>
      <template #display_value="{ record }">
        <span
          v-if="record.value !== null"
          class="mango-personal-config__value"
          :title="displayValue(record)"
        >
          {{ displayValue(record) }}
        </span>
        <span v-else class="mango-personal-config__empty">未设置</span>
      </template>
      <template #updated_at="{ record }">{{ record.updated_at || '-' }}</template>
      <template #actions="{ record }">
        <MangoTableActions :actions="configActions(record)" />
      </template>
      <template #empty>
        <div v-if="!loading && !failed" class="mango-empty-state">暂无个人配置</div>
      </template>
    </a-table>
  </section>
</template>

<script lang="ts" setup>
  import { reportLoadError } from '@/utils/load-error'

  import {
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    ref,
    shallowRef,
    watch,
  } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { clearUserConfig, getUserConfig } from '@/api/user/user'
  import useUserStore from '@/store/modules/user'
  import useUserPreferencesStore from '@/store/modules/user-preferences'
  import { useEnum } from '@/store/modules/get-enum'
  import { userConfigColumns, userConfigScrollX, userConfigValueTypes } from '../config'
  import type { UserConfigItem } from '../types'
  import { clearedConfigCount, formatDisplayValue, readUserConfigItems } from '../records'

  const userStore = useUserStore()
  const preferencesStore = useUserPreferencesStore()
  const enumStore = useEnum()
  function displayValue(item: UserConfigItem): string {
    if (item.value_type === 'environment') {
      const environment = enumStore.environment_type.find((value) => value.key === item.value)
      if (environment) return String(environment.title)
    }
    return formatDisplayValue(item.value)
  }
  const items = shallowRef<UserConfigItem[]>([])
  const loading = ref(false)
  const clearingKey = ref('')
  const failed = ref(false)
  const route = useRoute()
  let mounted = false,
    active = true,
    disposed = false,
    needsRead = true,
    contextVersion = 0,
    readVersion = 0,
    dialogVersion = 0
  let pending: { promise: Promise<void> } | null = null
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () =>
    !disposed &&
    active &&
    route.path === '/personal/info' &&
    (typeof document === 'undefined' || !document.hidden)
  function closeConfirmation(): void {
    dialogVersion++
    confirmation?.close()
    confirmation = null
  }
  function suspend(clear: boolean): void {
    contextVersion++
    readVersion++
    pending = null
    loading.value = false
    needsRead = true
    closeConfirmation()
    if (clear) {
      items.value = []
      failed.value = false
    }
  }
  function loadData(): Promise<void> {
    if (!mounted || !available()) return Promise.resolve()
    if (pending) return pending.promise
    const context = contextVersion,
      request = ++readVersion
    const current = () => available() && context === contextVersion && request === readVersion
    loading.value = true
    failed.value = false
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const response = await getUserConfig()
        if (!current()) return
        items.value = readUserConfigItems(response)
        needsRead = false
      } catch (loadFailure0) {
        if (current())
          reportLoadError(loadFailure0, '加载失败，请重试', false), (failed.value = true)
      } finally {
        if (current()) {
          loading.value = false
          pending = null
        }
      }
    })
    pending = { promise }
    return promise
  }

  function confirmClear(item: UserConfigItem): void {
    if (!available() || clearingKey.value || loading.value || failed.value) return
    if (item.key === 'interface' && (preferencesStore.saving || preferencesStore.dirty)) return
    if (!items.value.includes(item)) return
    closeConfirmation()
    const context = contextVersion,
      dialog = dialogVersion
    const current = () => available() && context === contextVersion && dialog === dialogVersion
    const key = item.key
    confirmation = Modal.confirm({
      title: `清除“${item.name}”`,
      content: '清除后，相关功能会恢复默认设置或需要重新选择。',
      okText: '清除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      onCancel: () => {
        dialogVersion++
        confirmation = null
      },
      onBeforeOk: async () => {
        if (!current() || clearingKey.value) return false
        clearingKey.value = key
        try {
          const count = clearedConfigCount(await clearUserConfig({ key }))
          if (!current()) return false
          // 清除环境会使本页上下文失效；随后按新环境重新读取，不沿用旧请求。
          if (count > 0 && key === 'selected_environment') userStore.selected_environment = null
          if (count > 0 && key === 'interface') await preferencesStore.reload()
          Message.success('个人配置已清除')
          if (pending) {
            readVersion++
            pending = null
            loading.value = false
          }
          await loadData()
          return true
        } catch (error) {
          if (current()) reportLoadError(error, '配置清除失败，请重试')
          return false
        } finally {
          clearingKey.value = ''
        }
      },
    })
  }

  function configActions(item: UserConfigItem) {
    return [
      {
        label: '清除',
        danger: true,
        disabled:
          !!clearingKey.value ||
          (item.key === 'interface' && (preferencesStore.saving || preferencesStore.dirty)) ||
          loading.value ||
          failed.value,
        loading: clearingKey.value === item.key,
        onClick: () => confirmClear(item),
      },
    ]
  }

  function resume(): void {
    if (mounted && needsRead) void loadData()
  }
  watch(
    () => [userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment],
    () => {
      suspend(true)
      void Promise.resolve().then(resume)
    },
    { flush: 'sync' }
  )
  watch(
    () => route.path,
    () => {
      suspend(false)
      void Promise.resolve().then(resume)
    },
    { flush: 'sync' }
  )
  function onVisibilityChange(): void {
    if (document.hidden) suspend(false)
    else resume()
  }
  onMounted(() => {
    mounted = true
    if (typeof document !== 'undefined')
      document.addEventListener('visibilitychange', onVisibilityChange)
    resume()
  })
  onActivated(() => {
    active = true
    resume()
  })
  onDeactivated(() => {
    active = false
    suspend(false)
  })
  onBeforeUnmount(() => {
    disposed = true
    suspend(true)
    if (typeof document !== 'undefined')
      document.removeEventListener('visibilitychange', onVisibilityChange)
  })
</script>

<style lang="less" scoped>
  .mango-personal-config {
    min-width: 0;
    margin-top: 0;
  }

  .mango-personal-config__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
    padding-bottom: var(--m-card-padding);
    margin-bottom: var(--m-page-gap);
    border-bottom: 1px solid var(--m-border);
  }

  .mango-personal-config__value,
  .mango-personal-config__empty {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-personal-config__empty {
    color: var(--m-muted);
  }
</style>
