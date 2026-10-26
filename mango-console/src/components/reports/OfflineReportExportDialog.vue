<template>
  <a-modal :visible="visible" title="导出离线 HTML" :width="560" :footer="false" @cancel="close">
    <a-alert>按当前结果生成离线 HTML，不会重新执行 Case。重试或排查更新后，可再次导出。</a-alert>
    <p role="status" :class="{ 'mango-offline-export__error': error }">{{ statusText }}</p>
    <div class="mango-offline-export__actions">
      <a-button size="small" @click="close">关闭</a-button>
      <a-button type="primary" size="small" :loading="downloading" @click="download">{{ downloaded ? '重新生成并下载' : '生成并下载' }}</a-button>
    </div>
  </a-modal>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { downloadOfflineReport } from '@/api/system/offline_report'
  import type { ReportSource } from '@/api/system/offline_report'

  const props = defineProps<{ visible: boolean; sourceKind: ReportSource; sourceId: string | number }>()
  const emit = defineEmits<{ (event: 'update:visible', value: boolean): void }>()
  const downloading = ref(false)
  const downloaded = ref(false)
  const error = ref('')
  let controller: AbortController | undefined
  const statusText = computed(() => error.value || (downloading.value ? '正在生成并下载，请稍候…' : downloaded.value ? '已发起 HTML 下载，保存后可断网打开阅读。' : '使用已保存的报告内容配置，文件不上传、不新增报告记录。'))

  function cancelRequest() { controller?.abort(); controller = undefined; downloading.value = false }
  function close() { cancelRequest(); emit('update:visible', false) }
  watch(() => [props.visible, props.sourceKind, props.sourceId], () => { cancelRequest(); downloaded.value = false; error.value = '' })
  onBeforeUnmount(cancelRequest)
  async function download() {
    if (downloading.value) return
    const request = new AbortController()
    controller = request
    downloading.value = true
    error.value = ''
    try {
      await downloadOfflineReport(props.sourceKind, props.sourceId, request.signal)
      if (!request.signal.aborted) downloaded.value = true
    } catch (cause) {
      if (!request.signal.aborted) error.value = cause instanceof Error ? cause.message : '生成或下载失败，请重试。'
    } finally {
      if (controller === request) { downloading.value = false; controller = undefined }
    }
  }
</script>
<style scoped>
  .mango-offline-export__actions { display: flex; justify-content: flex-end; gap: var(--m-space-sm); margin-top: 20px; }
  .mango-offline-export__error { color: var(--m-danger); overflow-wrap: anywhere; }
</style>
