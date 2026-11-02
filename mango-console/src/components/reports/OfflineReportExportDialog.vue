<template>
  <a-modal :visible="visible" title="导出离线 HTML" :width="560" :footer="false" @cancel="close">
    <div v-if="selectReport" class="mango-offline-export__selection">
      <a-form layout="horizontal">
        <a-form-item label="执行报告" required>
          <a-select v-model="selectedId" :loading="optionsLoading" :disabled="downloading"
            placeholder="请选择已完成的执行报告" allow-search @dropdown-reach-bottom="loadMoreOptions">
            <a-option v-for="item in options" :key="item.id" :value="item.id" :label="optionLabel(item)" />
            <template #footer>
              <div class="mango-offline-export__load-more" role="status">
                <span v-if="optionsLoading">正在加载…</span>
                <a-button v-else-if="optionsError" size="small" @click.stop="retryOptions">加载失败，点击重试</a-button>
                <span v-else-if="page * 20 < total">向下滚动加载更多</span>
                <span v-else-if="options.length">已加载全部 {{ total }} 条</span>
              </div>
            </template>
          </a-select>
        </a-form-item>
      </a-form>
      <a-button v-if="optionsError && !options.length" size="small" :loading="optionsLoading" @click="retryOptions">重新加载</a-button>
      <p v-if="!options.length && (optionsError || !optionsLoading)" role="status"
        :class="{ 'mango-offline-export__error': optionsError }">{{ optionsError || '暂无已完成且保留的执行报告。' }}</p>
    </div>
    <a-alert>实时生成 HTML 报告，不会重新执行 Case。</a-alert>
    <p role="status" :class="{ 'mango-offline-export__error': error }">{{ statusText }}</p>
    <div v-if="links" class="mango-offline-export__result">
      <div class="mango-offline-export__links">
        <a :href="links.preview_url" target="_blank" rel="noopener noreferrer">在线预览</a>
        <a :href="links.download_url" target="_blank" rel="noopener noreferrer">下载 HTML</a>
      </div>
      <p class="mango-offline-export__expiry">链接有效至：{{ expiresAtText }}。请勿向无关人员转发。</p>
    </div>
    <div class="mango-offline-export__actions">
      <a-button size="small" @click="close">关闭</a-button>
      <a-button type="primary" size="small" :loading="downloading" :disabled="selectReport && !selectedId" @click="generate">{{ links || downloaded ? '重新生成' : '生成报告' }}</a-button>
    </div>
  </a-modal>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { downloadOfflineReport, generateOfflineReport, getOfflineReportOptions } from '@/api/system/offline_report'
  import type { OfflineReportLinks, OfflineReportOption, ReportSource } from '@/api/system/offline_report'
  import { isApiBusinessError } from '@/api/errors'
  import { useEnum } from '@/store/modules/get-enum'

  const props = defineProps<{ visible: boolean; sourceKind: ReportSource; sourceId: string | number; selectReport?: boolean }>()
  const emit = defineEmits<{ (event: 'update:visible', value: boolean): void }>()
  const downloading = ref(false)
  const downloaded = ref(false)
  const error = ref('')
  const links = ref<OfflineReportLinks | null>(null)
  const expiresAtText = computed(() => links.value ? new Date(links.value.expires_at).toLocaleString('zh-CN', { hour12: false }) : '')
  let controller: AbortController | undefined
  let optionsController: AbortController | undefined
  const enumStore = useEnum()
  const options = ref<OfflineReportOption[]>([])
  const selectedId = ref<string | number>()
  const page = ref(0)
  const total = ref(0)
  const optionsLoading = ref(false)
  const optionsError = ref('')
  function optionLabel(item: OfflineReportOption) {
    const environment = enumStore.environment_type.find((entry) => String(entry.key) === String(item.test_env))?.title || String(item.test_env)
    const status = enumStore.task_status.find((entry) => String(entry.key) === String(item.status))?.title || String(item.status)
    return `${environment} · ${item.started_at.replace('T', ' ').slice(0, 19)} · ${status} · ID ${item.id}`
  }
  async function loadOptions(append = false) {
    if (append && (optionsLoading.value || downloading.value || page.value * 20 >= total.value)) return
    optionsController?.abort()
    const request = new AbortController()
    optionsController = request
    optionsLoading.value = true
    optionsError.value = ''
    if (!append) { selectedId.value = undefined; options.value = []; page.value = 0; total.value = 0 }
    const nextPage = append ? page.value + 1 : 1
    try {
      const result = await getOfflineReportOptions(props.sourceKind, props.sourceId, nextPage, request.signal)
      if (!request.signal.aborted) {
        const existingIds = new Set(options.value.map(item => String(item.id)))
        options.value = [...options.value, ...result.items.filter(item => !existingIds.has(String(item.id)))]
        total.value = result.count
        page.value = nextPage
      }
    } catch (cause) {
      if (!request.signal.aborted) optionsError.value = cause instanceof Error ? cause.message : '读取执行报告失败，请重试。'
    } finally {
      if (optionsController === request) { optionsLoading.value = false; optionsController = undefined }
    }
  }
  function loadMoreOptions() { void loadOptions(true) }
  function retryOptions() { void loadOptions(page.value > 0) }
  const statusText = computed(() => error.value || (downloading.value ? '正在生成并上传，请稍候…' : links.value ? '报告已生成，可直接预览或下载。' : downloaded.value ? '当前为本地存储，已发起 HTML 下载；在线预览需配置 MinIO/TOS。' : '每次生成均使用最新结果，链接有效期沿用报告配置。'))

  function cancelRequest() {
    controller?.abort(); controller = undefined; downloading.value = false
    optionsController?.abort(); optionsController = undefined; optionsLoading.value = false
  }
  function close() { cancelRequest(); emit('update:visible', false) }
  watch(() => [props.visible, props.sourceKind, props.sourceId, props.selectReport], () => {
    cancelRequest(); downloaded.value = false; links.value = null; error.value = ''; optionsError.value = ''
    selectedId.value = undefined; options.value = []; page.value = 0; total.value = 0
    if (props.visible && props.selectReport) void loadOptions()
  }, { immediate: true })
  watch(selectedId, () => { downloaded.value = false; links.value = null; error.value = '' })
  onBeforeUnmount(cancelRequest)
  async function generate() {
    if (downloading.value || (props.selectReport && !selectedId.value)) return
    const request = new AbortController()
    controller = request
    downloading.value = true
    error.value = ''
    links.value = null
    downloaded.value = false
    try {
      const sourceId = props.selectReport ? selectedId.value! : props.sourceId
      try {
        const result = await generateOfflineReport(props.sourceKind, sourceId, request.signal)
        if (!request.signal.aborted) links.value = result
      } catch (cause) {
        if (request.signal.aborted || !isApiBusinessError(cause) || cause.code !== 40047) throw cause
        await downloadOfflineReport(props.sourceKind, sourceId, request.signal)
        if (!request.signal.aborted) downloaded.value = true
      }
    } catch (cause) {
      if (!request.signal.aborted) error.value = cause instanceof Error ? cause.message : '生成或上传失败，请重试。'
    } finally {
      if (controller === request) { downloading.value = false; controller = undefined }
    }
  }
</script>
<style scoped>
  .mango-offline-export__actions { display: flex; justify-content: flex-end; gap: var(--m-space-sm); margin-top: 20px; }
  .mango-offline-export__error { color: var(--m-danger); overflow-wrap: anywhere; }
  .mango-offline-export__selection { margin-bottom: 16px; }
  .mango-offline-export__load-more { padding: 8px 12px; text-align: center; color: var(--m-muted); font-size: 12px; }
  .mango-offline-export__result { margin-top: 12px; }
  .mango-offline-export__links { display: flex; flex-wrap: wrap; gap: var(--m-space-sm); }
  .mango-offline-export__links a { color: var(--m-primary); border: 1px solid var(--m-border); border-radius: var(--m-radius-md); padding: 4px 12px; text-decoration: none; }
  .mango-offline-export__links a:hover { border-color: var(--m-primary); background: var(--m-primary-soft); }
  .mango-offline-export__expiry { color: var(--m-muted); font-size: 12px; overflow-wrap: anywhere; margin-top: 8px; }
</style>
