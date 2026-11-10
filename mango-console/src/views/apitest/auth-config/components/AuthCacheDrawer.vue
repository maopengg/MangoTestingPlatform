<template>
  <a-drawer
    v-model:visible="cacheModal.visible"
    title="授权缓存"
    width="50%"
    :footer="false"
    unmount-on-close
  >
    <MangoPanelSpin :loading="cacheLoading">
      <template v-if="cacheError"><a-button size="small" @click="retry">重新加载</a-button></template>
      <div class="mango-auth-cache-drawer-body">
        <a-descriptions v-if="cacheModal.data" :column="1" bordered>
          <a-descriptions-item label="授权名称">{{ cacheModal.data.name }}</a-descriptions-item>
          <a-descriptions-item label="过期时间">{{
            cacheModal.data.expires_at || '-'
          }}</a-descriptions-item>
          <a-descriptions-item label="剩余分钟">{{
            cacheModal.data.remaining_minutes ?? '-'
          }}</a-descriptions-item>
          <a-descriptions-item label="最近刷新时间">
            {{ cacheModal.data.last_refresh_time || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="最近错误">
            {{ cacheModal.data.last_refresh_error || '-' }}
          </a-descriptions-item>
        </a-descriptions>
        <div v-if="cacheModal.data" class="mango-auth-cache-json-section">
          <div class="mango-auth-cache-json-title">缓存数据</div>
          <JsonDisplay :data="cacheModal.data.cache_data || {}" />
        </div>
      </div>
    </MangoPanelSpin>
  </a-drawer>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { getApiAuthConfigCache, postApiAuthConfigRefresh } from '@/api/apitest/auth-config'
  import type { AuthCache, AuthRecord } from '../types'
  const emit = defineEmits<{ (event: 'refreshed'): void }>()
  const cacheModal = reactive<{ visible: boolean; data: AuthCache | null }>({
    visible: false,
    data: null,
  })
  const cacheLoading = ref(false)
  const cacheError = ref('')
  let requestVersion = 0
  let selected: AuthRecord | null = null
  const refreshing = new Set<number>()
  async function open(record: AuthRecord, refresh = false) {
    if (refreshing.has(record.id)) return
    const request = ++requestVersion
    selected = record
    cacheModal.data = null
    cacheModal.visible = true
    cacheLoading.value = true
    cacheError.value = ''
    if (refresh) refreshing.add(record.id)
    try {
      const response = await (refresh
        ? postApiAuthConfigRefresh(record.id)
        : getApiAuthConfigCache(record.id))
      if (refresh) emit('refreshed')
      if (request !== requestVersion || !cacheModal.visible) return
      cacheModal.data = response.data
      if (refresh) Message.success(response.msg)
    } catch (error) {
      if (request === requestVersion)
        void (reportLoadError(error, "授权缓存加载失败，请重试", false), cacheError.value = error instanceof Error ? error.message : '授权缓存加载失败，请重试')
    } finally {
      refreshing.delete(record.id)
      if (request === requestVersion) cacheLoading.value = false
    }
  }
  function retry() {
    if (selected) void open(selected)
  }
  function close() {
    requestVersion++
    cacheModal.visible = false
    cacheLoading.value = false
  }
  watch(
    () => cacheModal.visible,
    (visible) => {
      if (!visible) close()
    }
  )
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open })
</script>
<style scoped>
  .mango-auth-cache-drawer-body {
    min-height: 0;
  }
  .mango-auth-cache-json-section {
    margin-top: var(--m-page-gap);
  }
  .mango-auth-cache-json-title {
    margin-bottom: var(--m-page-gap);
    color: var(--m-text);
    font-weight: 500;
  }
</style>
